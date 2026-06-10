import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const SEVERITY_STYLES = {
  critical: { bg: "rgba(255,71,87,0.12)",  color: "var(--danger)", label: "CRITICAL" },
  warning:  { bg: "rgba(255,171,0,0.12)",  color: "var(--warn)",   label: "WARNING"  },
};

const TYPE_LABELS = {
  BRUTE_FORCE:        "Brute Force",
  CREDENTIAL_STUFFING: "Credential Stuffing",
};

function SeverityBadge({ severity }) {
  const s = SEVERITY_STYLES[severity] ?? { bg: "rgba(90,95,114,0.15)", color: "var(--muted)", label: severity };
  return (
    <span style={{
      fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px",
      fontWeight: 700, background: s.bg, color: s.color,
      letterSpacing: "0.06em", whiteSpace: "nowrap",
    }}>
      {s.label}
    </span>
  );
}

function TypeBadge({ type }) {
  return (
    <span style={{
      fontSize: "0.65rem", padding: "2px 8px", borderRadius: "3px",
      fontWeight: 500, background: "rgba(74,158,255,0.1)", color: "var(--info)",
      whiteSpace: "nowrap",
    }}>
      {TYPE_LABELS[type] ?? type}
    </span>
  );
}

export default function ThreatDetectionPage() {
  const [data, setData]         = useState(null);
  const [error, setError]       = useState(null);
  const [lookback, setLookback] = useState(24);
  const [scanTick, setScanTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    axios.get(`${API}/api/v1/auth-anomalies`, { params: { lookback_hours: lookback } })
      .then(res => { if (!cancelled) { setError(null); setData(res.data); } })
      .catch(() => { if (!cancelled) setError("Failed to run threat scan."); });

    return () => { cancelled = true; };
  }, [lookback, scanTick]);

  const loading   = data === null && !error;
  const anomalies = data?.anomalies ?? [];
  const critical  = anomalies.filter(a => a.severity === "critical").length;
  const warnings  = anomalies.filter(a => a.severity === "warning").length;

  return (
    <div>
      {/* Summary cards */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        {[
          { label: "Critical Threats",  value: critical, color: critical > 0 ? "var(--danger)" : "var(--muted)" },
          { label: "Warnings",          value: warnings,  color: warnings > 0  ? "var(--warn)"   : "var(--muted)" },
          { label: "Total Findings",    value: anomalies.length, color: "var(--text)" },
        ].map(card => (
          <div key={card.label} className="panel" style={{ flex: 1, padding: "1rem 1.25rem" }}>
            <div style={{ fontSize: "0.62rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.4rem" }}>
              {card.label}
            </div>
            <div style={{ fontSize: "1.6rem", fontWeight: 700, color: card.color, fontFamily: "var(--font-mono)" }}>
              {loading ? "—" : card.value}
            </div>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Threat Scan Results</span>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <select
              value={lookback}
              onChange={e => { setData(null); setError(null); setLookback(Number(e.target.value)); }}
              style={{
                background: "var(--bg)", border: "1px solid var(--border2)", borderRadius: "4px",
                padding: "4px 8px", color: "var(--text)", fontSize: "0.72rem",
                fontFamily: "var(--font-mono)",
              }}
            >
              <option value={1}>Last 1 hour</option>
              <option value={6}>Last 6 hours</option>
              <option value={24}>Last 24 hours</option>
              <option value={72}>Last 72 hours</option>
            </select>
            <button className="btn" onClick={() => setScanTick(t => t + 1)}>
              ↻ Rescan
            </button>
          </div>
        </div>

        <div className="table-wrap">
          {loading && <div className="state-msg">Scanning auth events for threats...</div>}
          {error   && <div className="state-msg" style={{ color: "var(--danger)" }}>{error}</div>}

          {!loading && !error && anomalies.length === 0 && (
            <div className="state-msg">
              No threats detected in the last {lookback}h.
              {data?.source === "live" && <span style={{ color: "var(--muted)" }}> (live scan)</span>}
            </div>
          )}

          {!loading && !error && anomalies.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Detected</th>
                  <th>Severity</th>
                  <th>Type</th>
                  <th>Target</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => (
                  <tr key={i}>
                    <td style={{ color: "var(--muted)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                      {a.detected_at ? new Date(a.detected_at).toLocaleString() : "—"}
                    </td>
                    <td><SeverityBadge severity={a.severity} /></td>
                    <td><TypeBadge type={a.type} /></td>
                    <td style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                      {a.email ?? a.ip_address ?? "—"}
                    </td>
                    <td style={{ fontSize: "0.72rem", color: "var(--muted)", maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {a.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {!loading && data && (
          <div style={{ padding: "0.6rem 1.25rem", borderTop: "1px solid var(--border)", fontSize: "0.67rem", color: "var(--muted)", display: "flex", gap: "1rem" }}>
            <span>Source: <span style={{ color: data.source === "live" ? "var(--accent)" : "var(--warn)" }}>{data.source}</span></span>
            <span>Window: {data.lookback_hours}h</span>
            {data.source === "demo" && <span style={{ color: "var(--warn)" }}>Demo data — engineered scenarios</span>}
          </div>
        )}
      </div>

      {/* Detection rules info */}
      <div className="panel" style={{ marginTop: "1rem" }}>
        <div className="panel-header">
          <span className="panel-title">Active Detection Rules</span>
        </div>
        <div style={{ padding: "1rem 1.25rem", display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
          {[
            {
              type: "BRUTE_FORCE",
              label: "Brute Force",
              color: "var(--warn)",
              desc: "≥ 5 failed logins for a single account within 10 minutes",
            },
            {
              type: "CREDENTIAL_STUFFING",
              label: "Credential Stuffing",
              color: "var(--danger)",
              desc: "≥ 10 unique accounts targeted from one IP within 5 minutes",
            },
          ].map(rule => (
            <div key={rule.type} style={{ flex: 1, minWidth: 220, padding: "0.75rem 1rem", background: "var(--bg)", borderRadius: "6px", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, color: rule.color, marginBottom: "0.35rem", letterSpacing: "0.04em" }}>
                {rule.label}
              </div>
              <div style={{ fontSize: "0.72rem", color: "var(--muted)", lineHeight: 1.5 }}>
                {rule.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
