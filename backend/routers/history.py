from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data_sources import DataProvider, get_data_provider
from database import get_db
from models import AlertLog, User
from permissions import has_permission
from routers.auth import get_current_user

router = APIRouter()


def mask_email(email: str) -> str:
    """j***@example.com: enough to recognise, not enough to harvest."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


@router.get("/anomalies")
def get_anomaly_history(
    limit: int = Query(50, ge=1, le=200),
    provider: DataProvider = Depends(get_data_provider),
    db: Session = Depends(get_db),
):
    anomalies = provider.anomaly_history(db, limit)
    return {"count": len(anomalies), "anomalies": anomalies, "source": provider.name}


@router.get("/alerts")
def get_alert_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Recipients are other people's addresses; only user admins see them in full.
    show_recipients = has_permission(current_user.role, "users:read", db)
    rows = (
        db.query(AlertLog)
          .order_by(AlertLog.sent_at.desc())
          .limit(limit)
          .all()
    )
    return {
        "count": len(rows),
        "alerts": [
            {
                "id":              r.id,
                "recipient":       r.recipient if show_recipients else mask_email(r.recipient),
                "job_name":        r.job_name,
                "anomaly_count":   r.anomaly_count,
                "sent_at":         r.sent_at.isoformat() if r.sent_at else None,
                "sendgrid_status": r.sendgrid_status,
                "simulated":       r.simulated,
            }
            for r in rows
        ],
    }
