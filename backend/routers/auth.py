import hashlib
import os
import secrets
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AuthEvent, RefreshToken, User

router = APIRouter()

ALGORITHM                   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS   = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS",   "7"))
MAX_LOGIN_ATTEMPTS          = int(os.getenv("MAX_LOGIN_ATTEMPTS",           "5"))
LOCKOUT_MINUTES             = int(os.getenv("LOCKOUT_MINUTES",              "15"))

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _secret_key() -> str:
    key = os.getenv("VIGIL_JWT_SECRET")
    if not key:
        raise RuntimeError("VIGIL_JWT_SECRET is not set in .env")
    return key


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _extract_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _record_auth_event(db, request, event_type, email, user=None):
    db.add(AuthEvent(
        email=email,
        user_id=user.id if user else None,
        event_type=event_type,
        ip_address=_extract_ip(request),
        user_agent=request.headers.get("user-agent"),
    ))
    db.commit()


def _user_dict(user: User) -> dict:
    return {
        "id":       str(user.id),
        "email":    user.email,
        "role":     user.role,
        "demo_mode": user.demo_mode,
    }


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user.id), "email": user.email, "role": user.role, "exp": expire},
        _secret_key(),
        algorithm=ALGORITHM,
    )


def create_pre_auth_token(user_id: str) -> str:
    """Short-lived token issued after password verification when TOTP is required."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    return jwt.encode(
        {"sub": user_id, "stage": "pre_2fa", "exp": expire},
        _secret_key(),
        algorithm=ALGORITHM,
    )


def _issue_refresh_token(
    db: Session,
    user: User,
    request: Request,
    family_id=None,
) -> tuple[str, RefreshToken]:
    raw       = secrets.token_urlsafe(32)
    fid       = family_id if family_id else uuid_lib.uuid4()
    expires   = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    record    = RefreshToken(
        user_id    = user.id,
        token_hash = _hash_token(raw),
        family_id  = fid,
        expires_at = expires,
        ip_address = _extract_ip(request),
        user_agent = request.headers.get("user-agent"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return raw, record


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload    = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise credentials_exc
        user_id = uuid_lib.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exc

    user = db.query(User).filter(User.id == user_id, User.is_active).first()
    if not user:
        raise credentials_exc
    return user


# ── Request bodies ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/signup", status_code=201)
def signup(req: SignupRequest, request: Request, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    email    = _normalize_email(req.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email         = email,
        password_hash = pwd_context.hash(req.password),
        role          = "analyst",
        demo_mode     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _record_auth_event(db, request, "signup", email, user)

    from audit import log_action
    log_action(db, "user.signup", request, user=user, resource_type="user", resource_id=str(user.id))

    access_token, (refresh_raw, _) = create_access_token(user), _issue_refresh_token(db, user, request)
    return {
        "access_token":  access_token,
        "refresh_token": refresh_raw,
        "token_type":    "bearer",
        "user":          _user_dict(user),
    }


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    user  = db.query(User).filter(User.email == email, User.is_active).first()

    now = datetime.now(timezone.utc)

    # Check lockout before password verification
    if user and user.locked_until and user.locked_until > now:
        _record_auth_event(db, request, "login_failure", email, user)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, please try again later",
        )

    if not user or not pwd_context.verify(req.password, user.password_hash):
        _record_auth_event(db, request, "login_failure", email, user)

        if user and user.role != "admin":
            window_start  = now - timedelta(minutes=LOCKOUT_MINUTES)
            failure_count = db.query(AuthEvent).filter(
                AuthEvent.email      == email,
                AuthEvent.event_type == "login_failure",
                AuthEvent.created_at >= window_start,
            ).count()
            if failure_count >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                db.commit()
                from audit import log_action
                log_action(db, "user.locked", request, user=user, resource_type="user", resource_id=str(user.id))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.locked_until:
        user.locked_until = None

    user.last_login_at = now
    db.commit()

    _record_auth_event(db, request, "login_success", email, user)

    from audit import log_action
    log_action(db, "user.login", request, user=user, resource_type="user", resource_id=str(user.id))

    if user.totp_enabled:
        return {
            "requires_2fa": True,
            "temp_token":   create_pre_auth_token(str(user.id)),
        }

    access_token      = create_access_token(user)
    refresh_raw, _    = _issue_refresh_token(db, user, request)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_raw,
        "token_type":    "bearer",
        "user":          _user_dict(user),
    }


@router.post("/refresh")
def refresh_token(req: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = _hash_token(req.refresh_token)
    record     = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    now = datetime.now(timezone.utc)

    if record.is_revoked:
        # Token reuse — entire family is compromised; revoke all siblings
        db.query(RefreshToken).filter(RefreshToken.family_id == record.family_id).update(
            {"is_revoked": True, "revoked_at": now}
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected — all sessions revoked for security",
        )

    if record.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.query(User).filter(User.id == record.user_id, User.is_active).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Rotate: revoke old, issue new in same family
    record.is_revoked = True
    record.revoked_at = now
    db.commit()

    new_access      = create_access_token(user)
    new_refresh_raw, _ = _issue_refresh_token(db, user, request, family_id=record.family_id)

    return {
        "access_token":  new_access,
        "refresh_token": new_refresh_raw,
        "token_type":    "bearer",
    }


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    db.query(RefreshToken).filter(
        RefreshToken.user_id    == current_user.id,
        ~RefreshToken.is_revoked,
    ).update({"is_revoked": True, "revoked_at": now})
    db.commit()
    return {"message": "Logged out"}


@router.get("/sessions")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now     = datetime.now(timezone.utc)
    records = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id    == current_user.id,
            ~RefreshToken.is_revoked,
            RefreshToken.expires_at >  now,
        )
        .order_by(RefreshToken.created_at.desc())
        .all()
    )
    return {
        "sessions": [
            {
                "id":         str(r.id),
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in records
        ]
    }


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        sid = uuid_lib.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    record = db.query(RefreshToken).filter(
        RefreshToken.id      == sid,
        RefreshToken.user_id == current_user.id,
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Session not found")

    record.is_revoked = True
    record.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Session revoked"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        **_user_dict(current_user),
        "created_at":   current_user.created_at.isoformat()   if current_user.created_at   else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }
