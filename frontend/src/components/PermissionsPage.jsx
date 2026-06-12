import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const ROLE_COLORS = {
  admin:   { bg: "rgba(74,158,255,0.12)",  color: "var(--info)" },
  analyst: { bg: "rgba(90,95,114,0.18)",   color: "var(--muted)" },
};

export default function PermissionsPage() {
  const [data, setData]       = useState(null);
  const [error, setError]     = useState(null);
  const [working, setWorking] = useState(null); // "role:perm"
  const [tick, setTick]       = useState(0);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/api/v1/admin/permissions`)
      .then(res => { if (!cancelled) { setError(null); setData(res.data); } })
      .catch(() => { if (!cancelled) setError("Failed to load permissions."); });
    return () => { cancelled = true; };
  }, [tick]);

  const toggle = async (roleName, permName, currentlyGranted) => {
    const key = `${roleName}:${permName}`;
    setWorking(key);

    // Optimistic update
    setData(prev => ({
      ...prev,
      roles: prev.roles.map(r =>
        r.name !== roleName ? r : {
          ...r,
          permissions: r.permissions.map(p =>
            p.name !== permName ? p : { ...p, granted: !currentlyGranted }
          ),
        }
      ),
    }));

    try {
      if (currentlyGranted) {
        await axios.delete(`${API}/api/v1/admin/roles/${roleName}/permissions/${permName}`);
      } else {
        await axios.post(`${API}/api/v1/admin/roles/${roleName}/permissions/${permName}`);
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? "Action failed.");
      // Revert
      setData(null);
      setTick(t => t + 1);
    } finally {
      setWorking(null);
    }
  };

  const loading = data === null && !error;

  return (
    <div>
      {error && (
        <div style={{ padding: "0.75rem 1.25rem", color: "var(--danger)", fontSize: "0.75rem", marginBottom: "1rem" }}>{error}</div>
      )}

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Role Permission Matrix</span>
          <button className="btn" onClick={() => { setData(null); setTick(t => t + 1); }}>↻ Refresh</button>
        </div>

        <div className="table-wrap">
          {loading && <div className="state-msg">Loading permissions...</div>}
          {!loading && data && (
            <table>
              <thead>
                <tr>
                  <th style={{ minWidth: 180 }}>Permission</th>
                  {data.roles.map(r => (
                    <th key={r.name} style={{ textAlign: "center", minWidth: 100 }}>
                      <span style={{
                        fontSize: "0.65rem", padding: "2px 10px", borderRadius: "3px", fontWeight: 700,
                        background: ROLE_COLORS[r.name]?.bg ?? "rgba(90,95,114,0.15)",
                        color:      ROLE_COLORS[r.name]?.color ?? "var(--muted)",
                      }}>
                        {r.name}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.permissions.map(permName => (
                  <tr key={permName}>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text)" }}>
                      {permName}
                    </td>
                    {data.roles.map(r => {
                      const perm    = r.permissions.find(p => p.name === permName);
                      const granted = perm?.granted ?? false;
                      const key     = `${r.name}:${permName}`;
                      const busy    = working === key;
                      return (
                        <td key={r.name} style={{ textAlign: "center" }}>
                          <button
                            onClick={() => toggle(r.name, permName, granted)}
                            disabled={busy}
                            title={granted ? `Revoke ${permName} from ${r.name}` : `Grant ${permName} to ${r.name}`}
                            style={{
                              background:   "none",
                              border:       `1px solid ${granted ? "var(--accent)" : "rgba(90,95,114,0.3)"}`,
                              borderRadius: "3px",
                              cursor:       busy ? "not-allowed" : "pointer",
                              padding:      "3px 12px",
                              fontSize:     "0.75rem",
                              fontWeight:   700,
                              color:        granted ? "var(--accent)" : "var(--muted)",
                              opacity:      busy ? 0.5 : 1,
                              minWidth:     48,
                              transition:   "all 0.15s",
                            }}
                          >
                            {busy ? "…" : granted ? "✓" : "✗"}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div style={{ marginTop: "1rem", fontSize: "0.68rem", color: "var(--muted)", lineHeight: 1.6 }}>
        Changes take effect within 5 minutes as permission lookups are cached server-side.
        Audit events are emitted for every grant and revoke.
      </div>
    </div>
  );
}
