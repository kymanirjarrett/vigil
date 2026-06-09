import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const PAGE_SIZE = 50;

const ACTION_COLORS = {
  "user.login":      { bg: "rgba(0,229,160,0.1)",  color: "var(--accent)" },
  "user.signup":     { bg: "rgba(74,158,255,0.1)",  color: "var(--info)" },
  "alert.triggered": { bg: "rgba(245,166,35,0.12)", color: "var(--warn)" },
  "mode.toggled":    { bg: "rgba(90,95,114,0.2)",   color: "var(--muted)" },
};

function ActionBadge({ action }) {
  const style = ACTION_COLORS[action] ?? { bg: "rgba(90,95,114,0.15)", color: "var(--muted)" };
  return (
    <span style={{
      fontSize: "0.65rem", padding: "2px 8px", borderRadius: "3px",
      fontWeight: 500, background: style.bg, color: style.color, whiteSpace: "nowrap",
    }}>
      {action}
    </span>
  );
}

export default function AuditLogPage() {
  // null entries = initial loading state; [] = loaded with no results
  const [entries, setEntries]           = useState(null);
  const [total, setTotal]               = useState(0);
  const [fetchError, setFetchError]     = useState(null);
  const [page, setPage]                 = useState(1);
  const [filterAction, setFilterAction] = useState("");
  const [refreshTick, setRefreshTick]   = useState(0);

  useEffect(() => {
    let cancelled = false;
    const params = { page, page_size: PAGE_SIZE };
    if (filterAction) params.action = filterAction;

    axios.get(`${API}/api/v1/audit`, { params })
      .then(res => {
        if (cancelled) return;
        setFetchError(null);
        setEntries(res.data.entries);
        setTotal(res.data.total);
      })
      .catch(() => {
        if (!cancelled) setFetchError("Failed to load audit log.");
      });

    return () => { cancelled = true; };
  }, [page, filterAction, refreshTick]);

  const handleFilterChange = (e) => {
    setFilterAction(e.target.value);
    setPage(1);
    setEntries(null);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const loading = entries === null && !fetchError;

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Audit Log</span>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <select
            value={filterAction}
            onChange={handleFilterChange}
            style={{
              background: "var(--bg)", border: "1px solid var(--border2)", borderRadius: "4px",
              padding: "4px 8px", color: filterAction ? "var(--text)" : "var(--muted)",
              fontSize: "0.72rem", fontFamily: "var(--font-mono)",
            }}
          >
            <option value="">All actions</option>
            <option value="user.login">user.login</option>
            <option value="user.signup">user.signup</option>
            <option value="alert.triggered">alert.triggered</option>
            <option value="mode.toggled">mode.toggled</option>
          </select>
          <button className="btn" onClick={() => { setEntries(null); setRefreshTick(t => t + 1); }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      <div className="table-wrap">
        {loading && <div className="state-msg">Loading audit log...</div>}
        {fetchError && <div className="state-msg" style={{ color: "var(--danger)" }}>{fetchError}</div>}
        {!loading && !fetchError && entries.length === 0 && (
          <div className="state-msg">No audit events recorded yet.</div>
        )}
        {!loading && !fetchError && entries.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>User ID</th>
                <th>Resource</th>
                <th>IP Address</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id} style={{ cursor: "default" }}>
                  <td style={{ color: "var(--muted)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                    {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                  </td>
                  <td><ActionBadge action={e.action} /></td>
                  <td style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                    {e.user_id ? `${e.user_id.slice(0, 8)}…` : "system"}
                  </td>
                  <td style={{ fontSize: "0.72rem", color: "var(--accent)" }}>
                    {e.resource_type && e.resource_id
                      ? `${e.resource_type}/${e.resource_id.slice(0, 16)}`
                      : (e.resource_type ?? "—")}
                  </td>
                  <td style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                    {e.ip_address ?? "—"}
                  </td>
                  <td style={{ fontSize: "0.72rem", color: "var(--muted)", maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {e.metadata ? JSON.stringify(e.metadata) : "—"}
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
            onClick={() => { setPage(p => p - 1); setEntries(null); }}
            style={{ padding: "3px 10px", opacity: page <= 1 ? 0.4 : 1 }}
          >
            ← Prev
          </button>
          <span>Page {page} of {totalPages} ({total} total)</span>
          <button
            className="btn"
            disabled={page >= totalPages}
            onClick={() => { setPage(p => p + 1); setEntries(null); }}
            style={{ padding: "3px 10px", opacity: page >= totalPages ? 0.4 : 1 }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
