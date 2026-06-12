import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function isLocked(user) {
  if (!user.locked_until) return false;
  return new Date(user.locked_until) > new Date();
}

function StatusBadge({ user }) {
  if (!user.is_active) {
    return <span style={{ fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px", background: "rgba(90,95,114,0.2)", color: "var(--muted)", fontWeight: 600 }}>INACTIVE</span>;
  }
  if (isLocked(user)) {
    return <span style={{ fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px", background: "rgba(255,71,87,0.12)", color: "var(--danger)", fontWeight: 600 }}>LOCKED</span>;
  }
  return <span style={{ fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px", background: "rgba(0,229,160,0.1)", color: "var(--accent)", fontWeight: 600 }}>ACTIVE</span>;
}

function RoleBadge({ role }) {
  const isAdmin = role === "admin";
  return (
    <span style={{
      fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px", fontWeight: 600,
      background: isAdmin ? "rgba(74,158,255,0.12)" : "rgba(90,95,114,0.15)",
      color: isAdmin ? "var(--info)" : "var(--muted)",
    }}>
      {role}
    </span>
  );
}

export default function AdminUsersPage({ currentUserId }) {
  const [users, setUsers]       = useState(null);
  const [error, setError]       = useState(null);
  const [working, setWorking]   = useState(null); // user_id of in-flight action
  const [tick, setTick]         = useState(0);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/api/v1/admin/users`)
      .then(res => { if (!cancelled) { setError(null); setUsers(res.data.users); } })
      .catch(() => { if (!cancelled) setError("Failed to load users."); });
    return () => { cancelled = true; };
  }, [tick]);

  const refresh = () => { setUsers(null); setError(null); setTick(t => t + 1); };

  const isSelf = (u) => u.id === currentUserId;

  const patch = async (userId, body, optimisticFn) => {
    setWorking(userId);
    // Optimistic update
    setUsers(prev => prev.map(u => u.id === userId ? { ...u, ...optimisticFn(u) } : u));
    try {
      const res = await axios.patch(`${API}/api/v1/admin/users/${userId}`, body);
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, ...res.data } : u));
    } catch (err) {
      setError(err.response?.data?.detail ?? "Action failed.");
      refresh(); // revert to server state
    } finally {
      setWorking(null);
    }
  };

  const handleRoleToggle = (u) => {
    const newRole = u.role === "admin" ? "analyst" : "admin";
    patch(u.id, { role: newRole }, () => ({ role: newRole }));
  };

  const handleToggleActive = (u) => {
    patch(u.id, { is_active: !u.is_active }, () => ({ is_active: !u.is_active }));
  };

  const handleUnlock = async (u) => {
    setWorking(u.id);
    try {
      await axios.post(`${API}/api/v1/admin/users/${u.id}/unlock`);
      setUsers(prev => prev.map(x => x.id === u.id ? { ...x, locked_until: null } : x));
    } catch (err) {
      setError(err.response?.data?.detail ?? "Unlock failed.");
    } finally {
      setWorking(null);
    }
  };

  const handleRevokeSessions = async (u) => {
    setWorking(u.id);
    try {
      await axios.delete(`${API}/api/v1/admin/users/${u.id}/sessions`);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Session revocation failed.");
    } finally {
      setWorking(null);
    }
  };

  const loading = users === null && !error;
  const activeCount   = users ? users.filter(u => u.is_active).length  : 0;
  const lockedCount   = users ? users.filter(isLocked).length           : 0;
  const inactiveCount = users ? users.filter(u => !u.is_active).length  : 0;

  return (
    <div>
      {/* Summary cards */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {[
          { label: "Active Users",    value: loading ? "—" : activeCount,   color: "var(--accent)" },
          { label: "Locked Accounts", value: loading ? "—" : lockedCount,   color: lockedCount > 0 ? "var(--danger)" : "var(--muted)" },
          { label: "Inactive",        value: loading ? "—" : inactiveCount, color: inactiveCount > 0 ? "var(--muted)" : "var(--muted)" },
        ].map(c => (
          <div key={c.label} className="panel" style={{ flex: 1, padding: "1rem 1.25rem", minWidth: 140 }}>
            <div style={{ fontSize: "0.62rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.4rem" }}>{c.label}</div>
            <div style={{ fontSize: "1.75rem", fontWeight: 700, color: c.color, fontFamily: "var(--font-mono)" }}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">All Users</span>
          <button className="btn" onClick={refresh}>↻ Refresh</button>
        </div>

        {error && (
          <div style={{ padding: "0.75rem 1.25rem", color: "var(--danger)", fontSize: "0.75rem" }}>{error}</div>
        )}

        <div className="table-wrap">
          {loading && <div className="state-msg">Loading users...</div>}
          {!loading && !error && users?.length === 0 && <div className="state-msg">No users found.</div>}
          {!loading && users?.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Last Login</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => {
                  const busy = working === u.id;
                  const self = isSelf(u);
                  return (
                    <tr key={u.id} style={{ opacity: busy ? 0.6 : 1 }}>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                        {u.email}
                        {self && (
                          <span style={{ marginLeft: "0.5rem", fontSize: "0.6rem", color: "var(--muted)", fontStyle: "italic" }}>you</span>
                        )}
                      </td>
                      <td><RoleBadge role={u.role} /></td>
                      <td><StatusBadge user={u} /></td>
                      <td style={{ fontSize: "0.72rem", color: "var(--muted)", whiteSpace: "nowrap" }}>
                        {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : "—"}
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                          {!self && (
                            <>
                              {/* Role toggle */}
                              <button
                                className="btn"
                                disabled={busy}
                                onClick={() => handleRoleToggle(u)}
                                style={{ fontSize: "0.65rem", padding: "3px 8px" }}
                                title={`Change to ${u.role === "admin" ? "analyst" : "admin"}`}
                              >
                                → {u.role === "admin" ? "analyst" : "admin"}
                              </button>

                              {/* Deactivate / Reactivate */}
                              <button
                                className="btn"
                                disabled={busy}
                                onClick={() => handleToggleActive(u)}
                                style={{
                                  fontSize: "0.65rem", padding: "3px 8px",
                                  color: u.is_active ? "var(--danger)" : "var(--accent)",
                                  borderColor: u.is_active ? "var(--danger)" : "var(--accent)",
                                }}
                              >
                                {u.is_active ? "Deactivate" : "Reactivate"}
                              </button>

                              {/* Unlock — only shown when locked */}
                              {isLocked(u) && (
                                <button
                                  className="btn"
                                  disabled={busy}
                                  onClick={() => handleUnlock(u)}
                                  style={{ fontSize: "0.65rem", padding: "3px 8px", color: "var(--warn)", borderColor: "var(--warn)" }}
                                >
                                  Unlock
                                </button>
                              )}

                              {/* Revoke sessions */}
                              <button
                                className="btn"
                                disabled={busy}
                                onClick={() => handleRevokeSessions(u)}
                                style={{ fontSize: "0.65rem", padding: "3px 8px", color: "var(--muted)" }}
                                title="Revoke all active sessions"
                              >
                                ⊗ Sessions
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
