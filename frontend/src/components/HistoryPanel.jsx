import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

const TABS = { ANOMALIES: "anomalies", ALERTS: "alerts" };

const SEVERITY_STYLE = {
  critical: { background: "rgba(255,71,87,0.15)",  color: "var(--danger)" },
  warning:  { background: "rgba(245,166,35,0.15)", color: "var(--warn)"   },
};

export default function HistoryPanel() {
  const [tab, setTab]           = useState(TABS.ANOMALIES);
  const [anomalies, setAnomalies] = useState([]);
  const [alerts, setAlerts]     = useState([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);

  const fetchHistory = async (activeTab) => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === TABS.ANOMALIES) {
        const res = await axios.get(`${API}/api/history/anomalies`);
        setAnomalies(res.data.anomalies);
      } else {
        const res = await axios.get(`${API}/api/history/alerts`);
        setAlerts(res.data.alerts);
      }
    } catch {
      setError("Failed to load history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHistory(tab); }, [tab]);

  const activeStyle = { borderColor: "var(--accent)", color: "var(--accent)" };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Event History</span>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            className="btn"
            style={tab === TABS.ANOMALIES ? activeStyle : {}}
            onClick={() => setTab(TABS.ANOMALIES)}
          >
            Anomaly Events
          </button>
          <button
            className="btn"
            style={tab === TABS.ALERTS ? activeStyle : {}}
            onClick={() => setTab(TABS.ALERTS)}
          >
            Alert Sends
          </button>
          <button className="btn" onClick={() => fetchHistory(tab)}>↻</button>
        </div>
      </div>

      <div className="table-wrap">
        {loading && <div className="state-msg">Loading history...</div>}
        {error   && <div className="state-msg" style={{ color: "var(--danger)" }}>{error}</div>}

        {!loading && !error && tab === TABS.ANOMALIES && (
          anomalies.length === 0
            ? <div className="state-msg">No anomaly events recorded yet.</div>
            : (
              <table>
                <thead>
                  <tr>
                    <th>Detected At</th>
                    <th>Job</th>
                    <th>Run ID</th>
                    <th>Type</th>
                    <th>Severity</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((a) => {
                    const sev = SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.warning;
                    return (
                      <tr key={a.id} style={{ cursor: "default" }}>
                        <td style={{ color: "var(--muted)", fontSize: "0.72rem" }}>
                          {a.detected_at ? new Date(a.detected_at).toLocaleString() : "—"}
                        </td>
                        <td style={{ color: "var(--accent)" }}>{a.job_name}</td>
                        <td style={{ color: "var(--muted)", fontSize: "0.72rem", fontFamily: "var(--font-mono)" }}>
                          {a.run_id?.slice(0, 18)}…
                        </td>
                        <td>
                          <span style={{
                            fontSize: "0.65rem", padding: "2px 7px", borderRadius: "3px",
                            fontWeight: 500, ...sev
                          }}>
                            {a.type.replace("_", " ")}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: "0.72rem", fontWeight: 600, ...sev }}>
                            {a.severity?.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ fontSize: "0.75rem", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {a.message}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )
        )}

        {!loading && !error && tab === TABS.ALERTS && (
          alerts.length === 0
            ? <div className="state-msg">No alert sends recorded yet.</div>
            : (
              <table>
                <thead>
                  <tr>
                    <th>Sent At</th>
                    <th>Recipient</th>
                    <th>Job</th>
                    <th>Anomalies</th>
                    <th>SendGrid Status</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a) => (
                    <tr key={a.id} style={{ cursor: "default" }}>
                      <td style={{ color: "var(--muted)", fontSize: "0.72rem" }}>
                        {a.sent_at ? new Date(a.sent_at).toLocaleString() : "—"}
                      </td>
                      <td style={{ fontSize: "0.75rem" }}>{a.recipient}</td>
                      <td style={{ color: "var(--accent)" }}>{a.job_name}</td>
                      <td style={{ color: "var(--warn)" }}>{a.anomaly_count}</td>
                      <td>
                        <span style={{
                          fontSize: "0.68rem", padding: "2px 8px", borderRadius: "3px",
                          background: a.sendgrid_status === 202
                            ? "rgba(0,229,160,0.1)" : "rgba(255,71,87,0.12)",
                          color: a.sendgrid_status === 202
                            ? "var(--accent)" : "var(--danger)",
                        }}>
                          {a.sendgrid_status ?? "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
        )}
      </div>
    </div>
  );
}
