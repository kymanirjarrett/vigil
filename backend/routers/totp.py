import hashlib
import secrets
from datetime import datetime, timezone

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import BackupCode, User
from routers.auth import (
    ALGORITHM,
    _issue_refresh_token,
    _record_auth_event,
    _secret_key,
    _user_dict,
    create_access_token,
    get_current_user,
)

router = APIRouter()

_ISSUER = "Vigil"


# ── helpers ───────────────────────────────────────────────────────────────────

def _decode_pre_auth_token(token: str) -> str:
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        if payload.get("stage") != "pre_2fa":
            raise ValueError("wrong stage")
        return payload["sub"]
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired 2FA session")


def _normalize_code(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")


def _make_backup_codes(db: Session, user_id) -> list[str]:
    db.query(BackupCode).filter(BackupCode.user_id == user_id).delete()
    codes = []
    for _ in range(8):
        raw = secrets.token_hex(4).upper()   # 8-char hex, e.g. "A1B2C3D4"
        db.add(BackupCode(
            user_id   = user_id,
            code_hash = hashlib.sha256(raw.encode()).hexdigest(),
        ))
        codes.append(f"{raw[:4]}-{raw[4:]}")  # display as "A1B2-C3D4"
    db.commit()
    return codes


def _verify_code(user: User, raw_code: str, db: Session) -> bool:
    normalized = _normalize_code(raw_code)

    # TOTP (6 digits)
    if user.totp_secret and normalized.isdigit() and len(normalized) == 6:
        return pyotp.TOTP(user.totp_secret).verify(normalized, valid_window=1)

    # Backup code (8 hex chars after stripping dash)
    if len(normalized) == 8:
        code_hash = hashlib.sha256(normalized.encode()).hexdigest()
        record = db.query(BackupCode).filter(
            BackupCode.user_id   == user.id,
            BackupCode.code_hash == code_hash,
            ~BackupCode.used,
        ).first()
        if record:
            record.used    = True
            record.used_at = datetime.now(timezone.utc)
            db.commit()
            return True

    return False


# ── request bodies ─────────────────────────────────────────────────────────────

class ConfirmBody(BaseModel):
    code: str


class VerifyLoginBody(BaseModel):
    temp_token: str
    code: str


class DisableBody(BaseModel):
    code: str


# ── endpoints ──────────────────────────────────────────────────────────────────

@router.get("/totp/status")
def totp_status(current_user: User = Depends(get_current_user)):
    return {"enabled": current_user.totp_enabled}


@router.post("/totp/enroll")
def totp_enroll(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    secret = pyotp.random_base32()
    uri    = pyotp.TOTP(secret).provisioning_uri(
        name        = current_user.email,
        issuer_name = _ISSUER,
    )
    current_user.totp_secret  = secret
    current_user.totp_enabled = False   # not yet confirmed
    db.commit()
    return {"secret": secret, "uri": uri}


@router.post("/totp/confirm")
def totp_confirm(
    body: ConfirmBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="No pending TOTP enrollment — call /totp/enroll first")

    normalized = _normalize_code(body.code)
    if not (normalized.isdigit() and len(normalized) == 6):
        raise HTTPException(status_code=400, detail="Code must be a 6-digit number")

    if not pyotp.TOTP(current_user.totp_secret).verify(normalized, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.totp_enabled = True
    db.commit()

    backup_codes = _make_backup_codes(db, current_user.id)

    from audit import log_action
    log_action(db, "user.totp_enabled", request, user=current_user,
               resource_type="user", resource_id=str(current_user.id))

    return {"backup_codes": backup_codes}


@router.post("/totp/disable")
def totp_disable(
    body: DisableBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    if not _verify_code(current_user, body.code, db):
        raise HTTPException(status_code=400, detail="Invalid code")

    current_user.totp_enabled = False
    current_user.totp_secret  = None
    db.query(BackupCode).filter(BackupCode.user_id == current_user.id).delete()
    db.commit()

    from audit import log_action
    log_action(db, "user.totp_disabled", request, user=current_user,
               resource_type="user", resource_id=str(current_user.id))

    return {"message": "2FA disabled"}


@router.post("/totp/backup-codes")
def regenerate_backup_codes(
    body: ConfirmBody,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    if not _verify_code(current_user, body.code, db):
        raise HTTPException(status_code=400, detail="Invalid code")

    backup_codes = _make_backup_codes(db, current_user.id)

    from audit import log_action
    log_action(db, "user.backup_codes_regenerated", request, user=current_user,
               resource_type="user", resource_id=str(current_user.id))

    return {"backup_codes": backup_codes}


@router.post("/totp/verify-login")
def totp_verify_login(
    body: VerifyLoginBody,
    request: Request,
    db: Session = Depends(get_db),
):
    user_id = _decode_pre_auth_token(body.temp_token)

    user = db.query(User).filter(User.id == user_id, User.is_active).first()
    if not user or not user.totp_enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    if not _verify_code(user, body.code, db):
        _record_auth_event(db, request, "login_failure_2fa", user.email, user)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code")

    _record_auth_event(db, request, "login_success", user.email, user)

    access_token    = create_access_token(user)
    refresh_raw, _  = _issue_refresh_token(db, user, request)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_raw,
        "token_type":    "bearer",
        "user":          _user_dict(user),
    }
