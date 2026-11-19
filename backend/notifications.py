"""Alert delivery.

In seed mode alerts are simulated: the scan still runs and the alert is recorded
in alert_log, but no email is sent. Otherwise anyone using the public app could
send email to arbitrary addresses. Real SendGrid delivery only happens when
DATA_SOURCE=aws.
"""
import os
from dataclasses import dataclass
from functools import lru_cache

import settings


@dataclass(frozen=True)
class AlertDelivery:
    simulated: bool
    status_code: int | None  # SendGrid HTTP status; None when simulated


class AlertConfigError(Exception):
    """Email delivery is not configured (missing API key or sender)."""


class SimulatedAlertSender:
    def send(self, recipient: str, job_name: str, anomalies: list) -> AlertDelivery:
        return AlertDelivery(simulated=True, status_code=None)


class SendGridAlertSender:
    def send(self, recipient: str, job_name: str, anomalies: list) -> AlertDelivery:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        api_key = os.getenv("SENDGRID_API_KEY")
        sender  = os.getenv("ALERT_SENDER_EMAIL")
        if not api_key or not sender:
            raise AlertConfigError("SENDGRID_API_KEY and ALERT_SENDER_EMAIL must be set")

        html_body = self._render(job_name, anomalies)
        message = Mail(
            from_email=sender,
            to_emails=recipient,
            subject=f"[Vigil Alert] {len(anomalies)} anomal{'ies' if len(anomalies) != 1 else 'y'} detected on {job_name}",
            html_content=html_body,
        )
        response = sendgrid.SendGridAPIClient(api_key=api_key).send(message)
        return AlertDelivery(simulated=False, status_code=response.status_code)

    @staticmethod
    def _render(job_name: str, anomalies: list) -> str:
        dashboard_url = os.getenv("FRONTEND_URL", "https://vigil-etl.vercel.app")
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

        return f"""
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
                <a href="{dashboard_url}" style="color:#00e5a0;text-decoration:none;">Open Dashboard</a>
              </p>
            </div>

          </div>
        </body>
        </html>
        """


@lru_cache(maxsize=1)
def get_alert_sender():
    if settings.DATA_SOURCE == "aws":
        return SendGridAlertSender()
    return SimulatedAlertSender()
