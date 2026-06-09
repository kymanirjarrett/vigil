from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from aws_client import get_glue_client
from botocore.exceptions import ClientError
from routers.anomalies import detect_anomalies
from database import get_db
from models import AlertLog, User
from permissions import require_permission
from demo_data import get_demo_runs
import sendgrid
from sendgrid.helpers.mail import Mail
import os

router = APIRouter()


class AlertRequest(BaseModel):
    job_name: str
    recipient_email: str


def send_alert_email(recipient: str, job_name: str, anomalies: list):
    """Send anomaly alert email via SendGrid."""
    api_key = os.getenv("SENDGRID_API_KEY")
    sender  = os.getenv("ALERT_SENDER_EMAIL")

    if not api_key or not sender:
        raise ValueError("SENDGRID_API_KEY and ALERT_SENDER_EMAIL must be set in .env")

    # Build anomaly rows for the email
    anomaly_rows = ""
    for a in anomalies:
        severity_color = "#ff4757" if a["severity"] == "critical" else "#f5a623"
        anomaly_rows += f"""
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2028;color:#e8eaf0;">{a['type'].replace('_', ' ')}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2028;">
            <span style="color:{severity_color};font-weight:600;">{a['severity'].upper()}</span>
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e2028;color:#e8eaf0;">{a['message']}</td>
        </tr>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#0a0b0d;font-family:'Courier New',monospace;">
      <div style="max-width:600px;margin:40px auto;background:#111318;border:1px solid #1e2028;border-radius:8px;overflow:hidden;">

        <!-- Header -->
        <div style="padding:24px 28px;border-bottom:1px solid #1e2028;display:flex;align-items:center;gap:12px;">
          <span style="font-size:20px;color:#00e5a0;">◈</span>
          <span style="font-size:14px;font-weight:700;color:#e8eaf0;letter-spacing:0.15em;">VIGIL</span>
          <span style="font-size:11px;color:#5a5f72;border-left:1px solid #2a2d38;padding-left:12px;letter-spacing:0.08em;">
            ETL OBSERVABILITY PLATFORM
          </span>
        </div>

        <!-- Alert Banner -->
        <div style="padding:20px 28px;background:rgba(255,71,87,0.07);border-bottom:1px solid rgba(255,71,87,0.2);">
          <div style="font-size:11px;color:#ff4757;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">
            ⚠ Anomalies Detected
          </div>
          <div style="font-size:22px;font-weight:700;color:#e8eaf0;margin-bottom:4px;">
            {len(anomalies)} alert{"s" if len(anomalies) != 1 else ""} on <span style="color:#00e5a0;">{job_name}</span>
          </div>
          <div style="font-size:12px;color:#5a5f72;">
            Vigil has detected unusual activity in your Glue pipeline.
          </div>
        </div>

        <!-- Anomaly Table -->
        <div style="padding:20px 28px;">
          <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <thead>
              <tr>
                <th style="text-align:left;padding:8px 16px;font-size:10px;letter-spacing:0.1em;color:#5a5f72;text-transform:uppercase;border-bottom:1px solid #2a2d38;">Type</th>
                <th style="text-align:left;padding:8px 16px;font-size:10px;letter-spacing:0.1em;color:#5a5f72;text-transform:uppercase;border-bottom:1px solid #2a2d38;">Severity</th>
                <th style="text-align:left;padding:8px 16px;font-size:10px;letter-spacing:0.1em;color:#5a5f72;text-transform:uppercase;border-bottom:1px solid #2a2d38;">Details</th>
              </tr>
            </thead>
            <tbody>
              {anomaly_rows}
            </tbody>
          </table>
        </div>

        <!-- Footer -->
        <div style="padding:16px 28px;border-top:1px solid #1e2028;">
          <p style="font-size:11px;color:#5a5f72;margin:0;">
            Sent by Vigil · AWS Region: us-east-2 · 
            <a href="http://localhost:5173" style="color:#00e5a0;text-decoration:none;">Open Dashboard</a>
          </p>
        </div>

      </div>
    </body>
    </html>
    """

    message = Mail(
        from_email=sender,
        to_emails=recipient,
        subject=f"[Vigil Alert] {len(anomalies)} anomal{'ies' if len(anomalies) != 1 else 'y'} detected on {job_name}",
        html_content=html_body,
    )

    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    response = sg.send(message)
    return response.status_code


@router.post("/trigger")
def trigger_alert(
    req: AlertRequest,
    current_user: User = Depends(require_permission("alerts:trigger")),
    db: Session = Depends(get_db),
):
    """Scan a job for anomalies and send an alert email if any are found."""
    use_demo = current_user.role == "analyst" or current_user.demo_mode

    try:
        if use_demo:
            runs = get_demo_runs(req.job_name)
        else:
            client = get_glue_client()
            response = client.get_job_runs(JobName=req.job_name, MaxResults=50)
            runs = [
                {
                    "run_id":         r["Id"],
                    "status":         r["JobRunState"],
                    "started_on":     str(r.get("StartedOn", "")),
                    "execution_time": r.get("ExecutionTime", 0),
                    "error_message":  r.get("ErrorMessage", None),
                }
                for r in response.get("JobRuns", [])
            ]

        anomalies = detect_anomalies(runs)

        if not anomalies:
            return {
                "sent":   False,
                "reason": "No anomalies detected — no alert sent.",
                "job":    req.job_name,
            }

        status_code = send_alert_email(req.recipient_email, req.job_name, anomalies)

        log_entry = AlertLog(
            recipient       = req.recipient_email,
            job_name        = req.job_name,
            anomaly_count   = len(anomalies),
            sendgrid_status = status_code,
        )
        db.add(log_entry)
        db.commit()

        return {
            "sent":            True,
            "anomaly_count":   len(anomalies),
            "recipient":       req.recipient_email,
            "sendgrid_status": status_code,
        }

    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send failed: {str(e)}")
