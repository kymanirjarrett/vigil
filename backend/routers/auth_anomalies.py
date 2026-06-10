from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth_detection import detect_auth_anomalies
from database import get_db
from demo_data import get_demo_auth_anomalies
from models import AuthEvent, User
from permissions import require_permission

router = APIRouter()


def _use_demo(user: User) -> bool:
    return user.role == "analyst" or user.demo_mode


@router.get("")
def get_auth_anomalies(
    lookback_hours: int = Query(24, ge=1, le=168, description="Hours of auth history to scan"),
    current_user: User = Depends(require_permission("security:read")),
    db: Session = Depends(get_db),
):
    if _use_demo(current_user):
        anomalies = get_demo_auth_anomalies()
        return {
            "anomaly_count": len(anomalies),
            "anomalies":     anomalies,
            "lookback_hours": lookback_hours,
            "source":        "demo",
        }

    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    rows = db.query(AuthEvent).filter(AuthEvent.created_at >= since).all()

    events = [
        {
            "email":      row.email,
            "event_type": row.event_type,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ]

    anomalies = detect_auth_anomalies(events)
    return {
        "anomaly_count": len(anomalies),
        "anomalies":     anomalies,
        "lookback_hours": lookback_hours,
        "source":        "live",
    }
