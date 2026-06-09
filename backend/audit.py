from fastapi import Request
from sqlalchemy.orm import Session
from models import AuditLogEntry, User
import uuid


def log_action(
    db: Session,
    action: str,
    request: Request,
    user: User = None,
    resource_type: str = None,
    resource_id: str = None,
    metadata: dict = None,
) -> None:
    """Append an immutable audit record. Never update or delete rows from audit_log."""
    ip = _extract_ip(request)
    ua = request.headers.get("user-agent")

    entry = AuditLogEntry(
        id=uuid.uuid4(),
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=metadata,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(entry)
    db.commit()


def _extract_ip(request: Request) -> str:
    # Render (and most proxies) set X-Forwarded-For; fall back to direct client IP.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
