import { useEffect, useState } from "react";
import { NavLink, Outlet, Link } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const NAV_ITEMS = [
  { to: "/app/dashboard",   label: "Dashboard",        icon: "◈", roles: ["admin", "analyst", "guest"] },
  { to: "/app/sessions",    label: "Sessions",         icon: "⊞", roles: ["admin", "analyst"] },
  { to: "/app/admin/users",        label: "User Management",  icon: "⊛", roles: ["admin"] },
  { to: "/app/admin/permissions",  label: "Permissions",      icon: "⊟", roles: ["admin"] },
  { to: "/app/posture",     label: "Security Posture", icon: "◉", roles: ["admin", "guest"] },
  { to: "/app/threats",     label: "Threat Detection", icon: "⚠", roles: ["admin", "guest"] },
  { to: "/app/security",    label: "Security Events",  icon: "⊙", roles: ["admin", "guest"] },
  { to: "/app/audit",       label: "Audit Log",        icon: "⊕", roles: ["admin", "guest"] },
];

export default function AppShell({ user, onLogout }) {
  const [collapsed, setCollapsed]   = useState(false);
  const [dataSource, setDataSource] = useState(null);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/health`)
      .then(res => { if (!cancelled) setDataSource(res.data.data_source); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

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

        {/* Footer: data source label, user info, sign out */}
        <div className="sidebar-footer">
          {dataSource === "seed" && (
            <div className="sidebar-data-label" title="This app runs on generated sample pipeline data">
              <span className="sidebar-data-dot" aria-hidden="true" />
              {!collapsed && <span className="sidebar-data-text">Sample data</span>}
            </div>
          )}

          {!collapsed && user && (
            <Link to="/app/account" style={{ textDecoration: "none" }}>
              <div className="sidebar-user" title="Account settings">
                <span className="sidebar-user-email">{user.email}</span>
                <span className={`sidebar-role-badge${user.role === "admin" ? " admin" : ""}`}>
                  {user.role}
                </span>
              </div>
            </Link>
          )}

          <button className="sidebar-signout" onClick={onLogout}>
            <span className="sidebar-link-icon">⊗</span>
            {!collapsed && <span className="sidebar-link-label">Sign out</span>}
          </button>
        </div>
      </aside>

      <main className="shell-main">
        <Outlet context={{ user }} />
      </main>
    </div>
  );
}
