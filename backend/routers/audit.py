from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from models import AuditLogEntry
from permissions import SecurityViewer, require_security_view
from security_seed import get_seed_audit_log

router = APIRouter()


@router.get("")
def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: str = Query(None),
    user_id: str = Query(None),
    since: datetime = Query(None),
    until: datetime = Query(None),
    viewer: SecurityViewer = Depends(require_security_view("audit:read")),
    db: Session = Depends(get_db),
):
    if viewer.sample:
        return get_seed_audit_log(action=action, page=page, page_size=page_size)

    q = db.query(AuditLogEntry).order_by(desc(AuditLogEntry.created_at))

    if action:
        q = q.filter(AuditLogEntry.action == action)
    if user_id:
        q = q.filter(AuditLogEntry.user_id == user_id)
    if since:
        q = q.filter(AuditLogEntry.created_at >= since)
    if until:
        q = q.filter(AuditLogEntry.created_at <= until)

    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "source": "live",
        "total": total,
        "page": page,
        "page_size": page_size,
        "entries": [
            {
                "id":            str(r.id),
                "user_id":       str(r.user_id) if r.user_id else None,
                "action":        r.action,
                "resource_type": r.resource_type,
                "resource_id":   r.resource_id,
                "metadata":      r.meta,
                "ip_address":    r.ip_address,
                "user_agent":    r.user_agent,
                "created_at":    r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
