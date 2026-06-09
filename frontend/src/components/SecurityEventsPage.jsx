import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const PAGE_SIZE = 50;

const EVENT_STYLES = {
  login_success: { bg: "rgba(0,229,160,0.1)",  color: "var(--accent)",  label: "login_success" },
  login_failure: { bg: "rgba(255,71,87,0.12)", color: "var(--danger)",  label: "login_failure" },
  signup:        { bg: "rgba(74,158,255,0.1)",  color: "var(--info)",    label: "signup" },
};

function EventBadge({ type }) {
  const s = EVENT_STYLES[type] ?? { bg: "rgba(90,95,114,0.15)", color: "var(--muted)", label: type };
  return (
    <span style={{
      fontSize: "0.65rem", padding: "2px 8px", borderRadius: "3px",
      fontWeight: 500, background: s.bg, color: s.color, whiteSpace: "nowrap",
    }}>
      {s.label}
    </span>
  );
}

export default function SecurityEventsPage() {
  const [events, setEvents]             = useState(null);
  const [total, setTotal]               = useState(0);
  const [fetchError, setFetchError]     = useState(null);
  const [page, setPage]                 = useState(1);
  const [filterType, setFilterType]     = useState("");
  const [refreshTick, setRefreshTick]   = useState(0);

  useEffect(() => {
    let cancelled = false;
    const params = { page, page_size: PAGE_SIZE };
    if (filterType) params.event_type = filterType;

    axios.get(`${API}/api/v1/auth-events`, { params })
      .then(res => {
        if (cancelled) return;
        setFetchError(null);
        setEvents(res.data.events);
        setTotal(res.data.total);
      })
      .catch(() => {
        if (!cancelled) setFetchError("Failed to load security events.");
      });

    return () => { cancelled = true; };
  }, [page, filterType, refreshTick]);

  const handleFilterChange = (e) => {
    setFilterType(e.target.value);
    setPage(1);
    setEvents(null);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const loading = events === null && !fetchError;

  const failures = events ? events.filter(e => e.event_type === "login_failure").length : 0;
  const successes = events ? events.filter(e => e.event_type === "login_success").length : 0;

  return (
    <div>
      {/* Summary cards */}
      {events && (
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
          {[
            { label: "Login Failures (page)", value: failures, color: failures > 0 ? "var(--danger)" : "var(--muted)" },
            { label: "Login Successes (page)", value: successes, color: "var(--accent)" },
            { label: "Total Events", value: total, color: "var(--text)" },
          ].map(card => (
            <div key={card.label} className="panel" style={{ flex: 1, padding: "1rem 1.25rem" }}>
              <div style={{ fontSize: "0.62rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.4rem" }}>
                {card.label}
              </div>
              <div style={{ fontSize: "1.6rem", fontWeight: 700, color: card.color, fontFamily: "var(--font-mono)" }}>
                {card.value}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Auth Event Log</span>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
            <select
              value={filterType}
              onChange={handleFilterChange}
              style={{
                background: "var(--bg)", border: "1px solid var(--border2)", borderRadius: "4px",
                padding: "4px 8px", color: filterType ? "var(--text)" : "var(--muted)",
                fontSize: "0.72rem", fontFamily: "var(--font-mono)",
              }}
            >
              <option value="">All event types</option>
              <option value="login_success">login_success</option>
              <option value="login_failure">login_failure</option>
              <option value="signup">signup</option>
            </select>
            <button className="btn" onClick={() => { setEvents(null); setRefreshTick(t => t + 1); }}>
              ↻ Refresh
            </button>
          </div>
        </div>

        <div className="table-wrap">
          {loading && <div className="state-msg">Loading security events...</div>}
          {fetchError && <div className="state-msg" style={{ color: "var(--danger)" }}>{fetchError}</div>}
          {!loading && !fetchError && events.length === 0 && (
            <div className="state-msg">No auth events recorded yet.</div>
          )}
          {!loading && !fetchError && events.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event</th>
                  <th>Email</th>
                  <th>IP Address</th>
                  <th>User Agent</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id} style={{ cursor: "default" }}>
                    <td style={{ color: "var(--muted)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                      {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                    </td>
                    <td><EventBadge type={e.event_type} /></td>
                    <td style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                      {e.email}
                    </td>
                    <td style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                      {e.ip_address ?? "—"}
                    </td>
                    <td style={{ fontSize: "0.68rem", color: "var(--muted)", maxWidth: 240, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {e.user_agent ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {!loading && totalPages > 1 && (
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", padding: "0.75rem 1.25rem", borderTop: "1px solid var(--border)", fontSize: "0.72rem", color: "var(--muted)" }}>
            <button
              className="btn"
              disabled={page <= 1}
              onClick={() => { setPage(p => p - 1); setEvents(null); }}
              style={{ padding: "3px 10px", opacity: page <= 1 ? 0.4 : 1 }}
            >
              ← Prev
            </button>
            <span>Page {page} of {totalPages} ({total} total)</span>
            <button
              className="btn"
              disabled={page >= totalPages}
              onClick={() => { setPage(p => p + 1); setEvents(null); }}
              style={{ padding: "3px 10px", opacity: page >= totalPages ? 0.4 : 1 }}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
