import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function SessionsPage() {
  const [sessions, setSessions] = useState(null);
  const [error, setError]       = useState(null);
  const [revoking, setRevoking] = useState(null);
  const [tick, setTick]         = useState(0);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/api/v1/auth/sessions`)
      .then(res  => { if (!cancelled) { setError(null); setSessions(res.data.sessions); } })
      .catch(()  => { if (!cancelled) setError("Failed to load sessions."); });
    return () => { cancelled = true; };
  }, [tick]);

  const refresh = () => { setSessions(null); setError(null); setTick(t => t + 1); };

  const handleRevoke = async (id) => {
    setRevoking(id);
    try {
      await axios.delete(`${API}/api/v1/auth/sessions/${id}`);
      setSessions(prev => prev.filter(s => s.id !== id));
    } catch {
      setError("Failed to revoke session.");
    } finally {
      setRevoking(null);
    }
  };

  const loading = sessions === null && !error;

  return (
    <div>
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="panel" style={{ flex: 1, padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: "0.62rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.4rem" }}>
            Active Sessions
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text)", fontFamily: "var(--font-mono)" }}>
            {loading ? "—" : sessions?.length ?? 0}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Your Sessions</span>
          <button className="btn" onClick={refresh}>↻ Refresh</button>
        </div>

        <div className="table-wrap">
          {loading && <div className="state-msg">Loading sessions...</div>}
          {error   && <div className="state-msg" style={{ color: "var(--danger)" }}>{error}</div>}
          {!loading && !error && sessions?.length === 0 && (
            <div className="state-msg">No active sessions.</div>
          )}
          {!loading && !error && sessions?.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Expires</th>
                  <th>IP Address</th>
                  <th>User Agent</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sessions.map(s => (
                  <tr key={s.id}>
                    <td style={{ color: "var(--muted)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                      {s.created_at ? new Date(s.created_at).toLocaleString() : "—"}
                    </td>
                    <td style={{ color: "var(--muted)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                      {s.expires_at ? new Date(s.expires_at).toLocaleString() : "—"}
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                      {s.ip_address ?? "—"}
                    </td>
                    <td style={{
                      fontSize: "0.68rem", color: "var(--muted)",
                      maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {s.user_agent ?? "—"}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className="btn"
                        onClick={() => handleRevoke(s.id)}
                        disabled={revoking === s.id}
                        style={{ color: "var(--danger)", borderColor: "var(--danger)", padding: "3px 10px", fontSize: "0.68rem" }}
                      >
                        {revoking === s.id ? "…" : "Revoke"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div style={{ padding: "0.75rem 1.25rem", borderTop: "1px solid var(--border)", fontSize: "0.67rem", color: "var(--muted)" }}>
          Sessions expire after {import.meta.env.VITE_REFRESH_TOKEN_EXPIRE_DAYS ?? 7} days. Revoking a session signs out that device immediately.
        </div>
      </div>
    </div>
  );
}
