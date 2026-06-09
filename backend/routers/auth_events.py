from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db
from models import AuthEvent, User
from permissions import require_permission
from datetime import datetime

router = APIRouter()

EVENT_TYPE_VALUES = ("login_success", "login_failure", "signup")


@router.get("")
def get_auth_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: str = Query(None, description="Filter by event type"),
    email: str = Query(None, description="Filter by email (exact match)"),
    since: datetime = Query(None),
    until: datetime = Query(None),
    _: User = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
):
    q = db.query(AuthEvent).order_by(desc(AuthEvent.created_at))

    if event_type:
        q = q.filter(AuthEvent.event_type == event_type)
    if email:
        q = q.filter(AuthEvent.email == email.strip().lower())
    if since:
        q = q.filter(AuthEvent.created_at >= since)
    if until:
        q = q.filter(AuthEvent.created_at <= until)

    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "events": [
            {
                "id":         str(r.id),
                "email":      r.email,
                "user_id":    str(r.user_id) if r.user_id else None,
                "event_type": r.event_type,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
