import os
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, AuthEvent

router = APIRouter()

ALGORITHM          = "HS256"
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_MINUTES    = int(os.getenv("LOCKOUT_MINUTES",    "15"))
ACCESS_TOKEN_EXPIRE_HOURS = 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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


def _record_auth_event(
    db: Session,
    request: Request,
    event_type: str,
    email: str,
    user: User = None,
) -> None:
    event = AuthEvent(
        email=email,
        user_id=user.id if user else None,
        event_type=event_type,
        ip_address=_extract_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    db.add(event)
    db.commit()


def _user_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "demo_mode": user.demo_mode,
    }


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user.id), "email": user.email, "role": user.role, "exp": expire},
        _secret_key(),
        algorithm=ALGORITHM,
    )


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
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
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


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str


@router.post("/signup", status_code=201)
def signup(req: SignupRequest, request: Request, db: Session = Depends(get_db)):
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    email = _normalize_email(req.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        password_hash=pwd_context.hash(req.password),
        role="analyst",
        demo_mode=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _record_auth_event(db, request, "signup", email, user)

    from audit import log_action
    log_action(db, "user.signup", request, user=user, resource_type="user", resource_id=str(user.id))

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": _user_dict(user),
    }


@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    user  = db.query(User).filter(User.email == email, User.is_active).first()

    # Check lockout before password verification
    now = datetime.now(timezone.utc)
    if user and user.locked_until and user.locked_until > now:
        _record_auth_event(db, request, "login_failure", email, user)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts, please try again later",
        )

    if not user or not pwd_context.verify(req.password, user.password_hash):
        # Record failure regardless of whether the email exists — needed for threat detection
        _record_auth_event(db, request, "login_failure", email, user)

        # Enforce lockout on non-admin accounts after repeated failures
        if user and user.role != "admin":
            window_start   = now - timedelta(minutes=LOCKOUT_MINUTES)
            failure_count  = db.query(AuthEvent).filter(
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

    # Clear any expired lockout on successful login
    if user.locked_until:
        user.locked_until = None

    user.last_login_at = now
    db.commit()

    _record_auth_event(db, request, "login_success", email, user)

    from audit import log_action
    log_action(db, "user.login", request, user=user, resource_type="user", resource_id=str(user.id))

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": _user_dict(user),
    }


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        **_user_dict(current_user),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }
