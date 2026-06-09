import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const ICONS = {
  DURATION_SPIKE: "⚡",
  CONSECUTIVE_FAILURES: "🔴",
};

const SEVERITY_STYLE = {
  critical: {
    border: "1px solid rgba(255,71,87,0.3)",
    background: "rgba(255,71,87,0.07)",
    color: "var(--danger)",
    tag: { background: "rgba(255,71,87,0.15)", color: "var(--danger)" },
  },
  warning: {
    border: "1px solid rgba(245,166,35,0.3)",
    background: "rgba(245,166,35,0.07)",
    color: "var(--warn)",
    tag: { background: "rgba(245,166,35,0.15)", color: "var(--warn)" },
  },
};

export default function AnomalyBanner() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState([]);

  const loadAnomalies = async () => {
    try {
      const res = await axios.get(`${API}/api/v1/anomalies/summary`);
      return res.data;
    } catch (e) {
      console.error("Anomaly fetch failed", e);
      throw e;
    }
  };

  const fetchAnomalies = async () => {
    setLoading(true);

    try {
      const summary = await loadAnomalies();
      setData(summary);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const summary = await loadAnomalies();
        if (!cancelled) {
          setData(summary);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || !data) return null;

  const visible = data.anomalies.filter((a) => !dismissed.includes(a.run_id));
  if (visible.length === 0) return null;

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.6rem",
        }}
      >
        <span
          style={{
            fontSize: "0.65rem",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--muted)",
          }}
        >
          ⚠ Anomalies Detected — {visible.length} alert
          {visible.length !== 1 ? "s" : ""}
        </span>
        <button
          className="btn"
          onClick={fetchAnomalies}
          style={{ fontSize: "0.65rem", padding: "3px 10px" }}
        >
          ↻ Re-scan
        </button>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {visible.map((a) => {
          const style = SEVERITY_STYLE[a.severity] ?? SEVERITY_STYLE.warning;
          return (
            <div
              key={a.run_id}
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "1rem",
                border: style.border,
                background: style.background,
                borderRadius: "5px",
                padding: "0.75rem 1rem",
              }}
            >
              <div
                style={{
                  display: "flex",
                  gap: "0.75rem",
                  alignItems: "flex-start",
                }}
              >
                <span style={{ fontSize: "1rem", lineHeight: 1.4 }}>
                  {ICONS[a.type] ?? "⚠"}
                </span>
                <div>
                  <div
                    style={{
                      display: "flex",
                      gap: "0.5rem",
                      alignItems: "center",
                      marginBottom: "3px",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "0.65rem",
                        padding: "1px 7px",
                        borderRadius: "3px",
                        fontWeight: 500,
                        ...style.tag,
                      }}
                    >
                      {a.type.replace("_", " ")}
                    </span>
                    {a.job_name && (
                      <span
                        style={{ fontSize: "0.68rem", color: "var(--muted)" }}
                      >
                        {a.job_name}
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--text)",
                      lineHeight: 1.5,
                    }}
                  >
                    {a.message}
                  </div>
                  {a.started_on && (
                    <div
                      style={{
                        fontSize: "0.68rem",
                        color: "var(--muted)",
                        marginTop: "2px",
                      }}
                    >
                      {new Date(a.started_on).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={() => setDismissed((d) => [...d, a.run_id])}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--muted)",
                  cursor: "pointer",
                  fontSize: "0.9rem",
                  padding: "0 4px",
                  flexShrink: 0,
                }}
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
