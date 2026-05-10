from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import AnomalyEvent, AlertLog

router = APIRouter()


@router.get("/anomalies")
def get_anomaly_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AnomalyEvent)
          .order_by(AnomalyEvent.detected_at.desc())
          .limit(limit)
          .all()
    )
    return {
        "count": len(rows),
        "anomalies": [
            {
                "id":          r.id,
                "job_name":    r.job_name,
                "run_id":      r.run_id,
                "type":        r.type,
                "severity":    r.severity,
                "message":     r.message,
                "detected_at": r.detected_at.isoformat() if r.detected_at else None,
            }
            for r in rows
        ],
    }


@router.get("/alerts")
def get_alert_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
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
                "recipient":       r.recipient,
                "job_name":        r.job_name,
                "anomaly_count":   r.anomaly_count,
                "sent_at":         r.sent_at.isoformat() if r.sent_at else None,
                "sendgrid_status": r.sendgrid_status,
            }
            for r in rows
        ],
    }
