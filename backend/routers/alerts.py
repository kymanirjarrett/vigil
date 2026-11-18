from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from anomaly_detection import detect_anomalies
from audit import log_action
from data_sources import DataProvider, get_data_provider
from database import get_db
from models import AlertLog, User
from notifications import AlertConfigError, get_alert_sender
from permissions import require_permission

router = APIRouter()


class AlertRequest(BaseModel):
    job_name: str
    recipient_email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/trigger")
def trigger_alert(
    req: AlertRequest,
    request: Request,
    current_user: User = Depends(require_permission("alerts:trigger")),
    provider: DataProvider = Depends(get_data_provider),
    sender=Depends(get_alert_sender),
    db: Session = Depends(get_db),
):
    """Scan a job for anomalies and send (or, on sample data, simulate) an alert."""
    anomalies = detect_anomalies(provider.get_runs(req.job_name, max_results=50))
    if not anomalies:
        return {"sent": False, "reason": "No anomalies detected, no alert sent.", "job": req.job_name}

    try:
        delivery = sender.send(req.recipient_email, req.job_name, anomalies)
    except AlertConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Email delivery failed")

    db.add(AlertLog(
        recipient       = req.recipient_email,
        job_name        = req.job_name,
        anomaly_count   = len(anomalies),
        sendgrid_status = delivery.status_code,
        simulated       = delivery.simulated,
    ))
    db.commit()

    log_action(db, "alert.triggered", request, user=current_user,
               resource_type="glue_job", resource_id=req.job_name,
               metadata={"anomaly_count": len(anomalies), "simulated": delivery.simulated})

    return {
        "sent":            True,
        "simulated":       delivery.simulated,
        "anomaly_count":   len(anomalies),
        "recipient":       req.recipient_email,
        "sendgrid_status": delivery.status_code,
    }
