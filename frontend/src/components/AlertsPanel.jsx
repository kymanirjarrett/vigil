import { useState } from "react";
import axios from "axios";
import { API } from "../api";

const ANALYST_PERMISSIONS = new Set(["jobs:read", "alerts:read", "anomalies:read"]);
const ADMIN_PERMISSIONS   = new Set([
  "jobs:read", "jobs:read:live", "alerts:read", "alerts:trigger",
  "anomalies:read", "users:read", "users:manage", "audit:read", "security:read",
]);

function userPermissions(user) {
  if (!user) return new Set();
  return user.role === "admin" ? ADMIN_PERMISSIONS : ANALYST_PERMISSIONS;
}

export default function AlertsPanel({ jobName, user }) {
  const [email, setEmail]     = useState("");
  const [status, setStatus]   = useState(null);
  const [message, setMessage] = useState("");

  const canTrigger = userPermissions(user).has("alerts:trigger");

  const triggerAlert = async () => {
    if (!jobName || !canTrigger) return;
    setStatus("sending");
    setMessage("");
    try {
      const res = await axios.post(`${API}/api/v1/alerts/trigger`, {
        job_name:        jobName,
        recipient_email: email,
      });
      if (res.data.sent) {
        const count = `${res.data.anomaly_count} anomal${res.data.anomaly_count !== 1 ? "ies" : "y"}`;
        setStatus(res.data.simulated ? "simulated" : "sent");
        setMessage(res.data.simulated
          ? `Alert simulated: ${count} recorded in history. No email is sent on sample data.`
          : `Alert sent to ${res.data.recipient}: ${count} reported.`);
      } else {
        setStatus("no_anomalies");
        setMessage(res.data.reason);
      }
    } catch (e) {
      setStatus("error");
      setMessage(e.response?.data?.detail ?? "Something went wrong.");
    }
  };

  const STATUS_CONFIG = {
    sent:         { color: "var(--accent)",  icon: "✓", label: "Alert sent" },
    simulated:    { color: "var(--info)",    icon: "✓", label: "Alert simulated" },
    no_anomalies: { color: "var(--info)",    icon: "✓", label: "No anomalies" },
    error:        { color: "var(--danger)",  icon: "✕", label: "Error" },
    sending:      { color: "var(--muted)",   icon: "…", label: "Sending" },
  };

  const cfg = status ? STATUS_CONFIG[status] : null;

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Alert Configuration</span>
      </div>

      <div style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "1rem" }}>

        <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
          Scanning job:{" "}
          <span style={{ color: jobName ? "var(--accent)" : "var(--muted)" }}>
            {jobName ?? "No job selected — click a job above first"}
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label style={{ fontSize: "0.65rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Recipient Email
          </label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            disabled={!canTrigger}
            style={{
              background: "var(--bg)",
              border: "1px solid var(--border2)",
              borderRadius: "4px",
              padding: "8px 12px",
              color: canTrigger ? "var(--text)" : "var(--muted)",
              fontFamily: "var(--font-mono)",
              fontSize: "0.8rem",
              outline: "none",
              width: "320px",
              opacity: canTrigger ? 1 : 0.5,
            }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          <div style={{ position: "relative", display: "inline-block" }}>
            <button
              className="btn"
              onClick={triggerAlert}
              disabled={!jobName || !canTrigger || !email || status === "sending"}
              title={!canTrigger ? "Your role has read-only access to alerts" : undefined}
              style={{
                borderColor: canTrigger && jobName ? "var(--accent)" : "var(--border2)",
                color:        canTrigger && jobName ? "var(--accent)" : "var(--muted)",
                padding:      "7px 18px",
                cursor:       canTrigger && jobName ? "pointer" : "not-allowed",
                opacity:      !canTrigger || status === "sending" ? 0.5 : 1,
              }}
            >
              {status === "sending" ? "Scanning…" : "⚡ Run Anomaly Scan & Alert"}
            </button>
          </div>

          {!canTrigger && (
            <span style={{ fontSize: "0.72rem", color: "var(--muted)", fontStyle: "italic" }}>
              Your role can view alerts but cannot trigger them.
            </span>
          )}

          {canTrigger && cfg && (
            <span style={{ fontSize: "0.75rem", color: cfg.color, display: "flex", alignItems: "center", gap: "6px" }}>
              <span>{cfg.icon}</span>
              <span>{message}</span>
            </span>
          )}
        </div>

        <p style={{ fontSize: "0.7rem", color: "var(--muted)", lineHeight: 1.6 }}>
          {canTrigger
            ? "Vigil will scan the selected job's run history for anomalies. If any are found, the alert is recorded in history and emailed via SendGrid. On sample data the email is simulated and nothing is sent."
            : "Alert triggering requires admin access. Contact your administrator to send alerts."}
        </p>
      </div>
    </div>
  );
}
