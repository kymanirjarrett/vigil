import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const NAV_ITEMS = [
  { to: "/app/dashboard",   label: "Dashboard",        icon: "◈", roles: ["admin", "analyst"] },
  { to: "/app/sessions",    label: "Sessions",         icon: "⊞", roles: ["admin", "analyst"] },
  { to: "/app/admin/users",        label: "User Management",  icon: "⊛", roles: ["admin"] },
  { to: "/app/admin/permissions",  label: "Permissions",      icon: "⊟", roles: ["admin"] },
  { to: "/app/posture",     label: "Security Posture", icon: "◉", roles: ["admin"] },
  { to: "/app/threats",     label: "Threat Detection", icon: "⚠", roles: ["admin"] },
  { to: "/app/security",    label: "Security Events",  icon: "⊙", roles: ["admin"] },
  { to: "/app/audit",       label: "Audit Log",        icon: "⊕", roles: ["admin"] },
];

export default function AppShell({ user, onLogout, onUserUpdate }) {
  const [modeKey, setModeKey]     = useState(0);
  const [toggling, setToggling]   = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const isDemo    = user?.role === "analyst" || user?.demo_mode;
  const canToggle = user?.role === "admin";

  const handleModeToggle = async () => {
    setToggling(true);
    try {
      const res = await axios.post(`${API}/api/v1/mode/toggle`);
      onUserUpdate({ ...user, demo_mode: res.data.demo_mode });
      setModeKey(k => k + 1);
    } catch (e) {
      console.error("Mode toggle failed", e);
    } finally {
      setToggling(false);
    }
  };

  const visibleNav = NAV_ITEMS.filter(n => n.roles.includes(user?.role));

  return (
    <div className={`shell${collapsed ? " shell-collapsed" : ""}`}>
      <aside className="sidebar">
        {/* Logo + collapse */}
        <div className="sidebar-logo-row">
          <div className="logo">
            <span className="logo-icon">◈</span>
            {!collapsed && <span className="logo-text">VIGIL</span>}
          </div>
          <button
            className="sidebar-collapse-btn"
            onClick={() => setCollapsed(c => !c)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? "›" : "‹"}
          </button>
        </div>

        {/* Nav links */}
        <nav className="sidebar-nav">
          {visibleNav.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            >
              <span className="sidebar-link-icon">{item.icon}</span>
              {!collapsed && <span className="sidebar-link-label">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Footer: mode toggle, user info, sign out */}
        <div className="sidebar-footer">
          {canToggle ? (
            <button
              className="sidebar-mode-btn"
              onClick={handleModeToggle}
              disabled={toggling}
              style={{
                borderColor: isDemo ? "var(--warn)" : "var(--accent)",
                color: isDemo ? "var(--warn)" : "var(--accent)",
              }}
              title={isDemo ? "Switch to Live" : "Switch to Demo"}
            >
              <span className="pulse" style={{ background: isDemo ? "var(--warn)" : undefined }} />
              {!collapsed && (
                <span>{toggling ? "…" : isDemo ? "DEMO — switch to LIVE" : "LIVE — switch to DEMO"}</span>
              )}
            </button>
          ) : (
            <div className="sidebar-mode-demo">
              <span className="pulse" style={{ background: "var(--warn)" }} />
              {!collapsed && <span>DEMO MODE</span>}
            </div>
          )}

          {!collapsed && user && (
            <div className="sidebar-user">
              <span className="sidebar-user-email">{user.email}</span>
              <span className={`sidebar-role-badge${user.role === "admin" ? " admin" : ""}`}>
                {user.role}
              </span>
            </div>
          )}

          <button className="sidebar-signout" onClick={onLogout}>
            <span className="sidebar-link-icon">⊗</span>
            {!collapsed && <span className="sidebar-link-label">Sign out</span>}
          </button>
        </div>
      </aside>

      <main className="shell-main">
        <Outlet context={{ user, modeKey }} />
      </main>
    </div>
  );
}
