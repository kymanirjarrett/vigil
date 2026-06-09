import { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import axios from "axios";
import LoginPage from "./components/LoginPage";
import SignupPage from "./components/SignupPage";
import JobsTable from "./components/JobsTable";
import JobRunsPanel from "./components/JobRunsPanel";
import AnomalyBanner from "./components/AnomalyBanner";
import AlertsPanel from "./components/AlertsPanel";
import HistoryPanel from "./components/HistoryPanel";
import AuditLogPage from "./components/AuditLogPage";
import "./App.css";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const _stored = localStorage.getItem("vigil_token");
const _storedUser = (() => {
  try { return JSON.parse(localStorage.getItem("vigil_user")); } catch { return null; }
})();

if (_stored) axios.defaults.headers.common["Authorization"] = `Bearer ${_stored}`;

function Dashboard({ onLogout, user, onUserUpdate }) {
  const [selectedJob, setSelectedJob] = useState(null);
  const [toggling, setToggling]       = useState(false);
  const [modeKey, setModeKey]         = useState(0);
  const [view, setView]               = useState("dashboard"); // "dashboard" | "audit"

  const isDemo = user?.role === "analyst" || user?.demo_mode;
  const canToggle = user?.role === "admin";

  const handleModeToggle = async () => {
    setToggling(true);
    try {
      const res = await axios.post(`${API}/api/v1/mode/toggle`);
      onUserUpdate({ ...user, demo_mode: res.data.demo_mode });
      // Clear selection and force all data panels to remount + refetch
      setSelectedJob(null);
      setModeKey(k => k + 1);
    } catch (e) {
      console.error("Mode toggle failed", e);
    } finally {
      setToggling(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">VIGIL</span>
          </div>
          <span className="logo-sub">ETL Observability Platform</span>
        </div>
        <div className="header-right">
          {/* Mode indicator / toggle */}
          {canToggle ? (
            <button
              className="btn"
              onClick={handleModeToggle}
              disabled={toggling}
              style={{
                fontSize: "0.65rem",
                padding: "4px 12px",
                borderColor: isDemo ? "var(--warn)" : "var(--accent)",
                color: isDemo ? "var(--warn)" : "var(--accent)",
              }}
            >
              {toggling ? "…" : isDemo ? "DEMO — switch to LIVE" : "LIVE — switch to DEMO"}
            </button>
          ) : (
            <span style={{
              fontSize: "0.6rem",
              padding: "3px 10px",
              borderRadius: "3px",
              background: "rgba(245,166,35,0.12)",
              color: "var(--warn)",
              letterSpacing: "0.08em",
              fontWeight: 600,
            }}>
              DEMO MODE
            </span>
          )}

          <div className="status-indicator">
            <span className="pulse" style={{ background: isDemo ? "var(--warn)" : undefined }} />
            <span className="status-text">{isDemo ? "DEMO" : "LIVE"}</span>
          </div>

          {!isDemo && <span className="region-badge">us-east-2</span>}

          {user && (
            <span style={{ fontSize: "0.68rem", color: "var(--muted)" }}>
              {user.email}
              <span style={{
                marginLeft: "6px",
                fontSize: "0.6rem",
                padding: "1px 6px",
                borderRadius: "3px",
                background: user.role === "admin" ? "rgba(0,229,160,0.12)" : "rgba(90,95,114,0.2)",
                color: user.role === "admin" ? "var(--accent)" : "var(--muted)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}>
                {user.role}
              </span>
            </span>
          )}

          {user?.role === "admin" && (
            <button
              className="btn"
              onClick={() => setView(v => v === "audit" ? "dashboard" : "audit")}
              style={{
                fontSize: "0.68rem",
                borderColor: view === "audit" ? "var(--accent)" : undefined,
                color: view === "audit" ? "var(--accent)" : undefined,
              }}
            >
              {view === "audit" ? "← Dashboard" : "Audit Log"}
            </button>
          )}
          <button className="btn" onClick={onLogout} style={{ fontSize: "0.68rem" }}>
            Sign out
          </button>
        </div>
      </header>

      <main className="main">
        {view === "audit" ? (
          <>
            <div className="page-title">
              <h1>Audit Log</h1>
              <p>Immutable record of all user actions — append-only</p>
            </div>
            <AuditLogPage />
          </>
        ) : (
          <>
            <div className="page-title">
              <h1>Glue Job Monitor</h1>
              <p>
                {isDemo
                  ? "Viewing synthetic demo data — anomalies are pre-engineered for demonstration"
                  : "Select a job to inspect its run history"}
              </p>
            </div>

            <AnomalyBanner key={`anomaly-${modeKey}`} />
            <JobsTable key={`jobs-${modeKey}`} onSelectJob={setSelectedJob} selectedJob={selectedJob} />

            {selectedJob && (
              <>
                <JobRunsPanel jobName={selectedJob} onClose={() => setSelectedJob(null)} />
                <AlertsPanel jobName={selectedJob} user={user} />
              </>
            )}

            <HistoryPanel />
          </>
        )}
      </main>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(_stored);
  const [user, setUser]   = useState(_storedUser);
  const navigate          = useNavigate();

  useEffect(() => {
    const id = axios.interceptors.response.use(
      res => res,
      err => {
        if (err.response?.status === 401) {
          delete axios.defaults.headers.common["Authorization"];
          localStorage.removeItem("vigil_token");
          localStorage.removeItem("vigil_user");
          setToken(null);
          setUser(null);
          navigate("/login");
        }
        return Promise.reject(err);
      }
    );
    return () => axios.interceptors.response.eject(id);
  }, [navigate]);

  const handleLogin = (newToken, userData) => {
    axios.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
    localStorage.setItem("vigil_token", newToken);
    if (userData) localStorage.setItem("vigil_user", JSON.stringify(userData));
    setToken(newToken);
    setUser(userData);
    navigate("/app");
  };

  const handleLogout = () => {
    delete axios.defaults.headers.common["Authorization"];
    localStorage.removeItem("vigil_token");
    localStorage.removeItem("vigil_user");
    setToken(null);
    setUser(null);
    navigate("/login");
  };

  const handleUserUpdate = (updatedUser) => {
    localStorage.setItem("vigil_user", JSON.stringify(updatedUser));
    setUser(updatedUser);
  };

  return (
    <Routes>
      <Route
        path="/login"
        element={token ? <Navigate to="/app" replace /> : <LoginPage onLogin={handleLogin} />}
      />
      <Route
        path="/signup"
        element={token ? <Navigate to="/app" replace /> : <SignupPage onLogin={handleLogin} />}
      />
      <Route
        path="/app"
        element={
          token
            ? <Dashboard onLogout={handleLogout} user={user} onUserUpdate={handleUserUpdate} />
            : <Navigate to="/login" replace />
        }
      />
      <Route
        path="*"
        element={<Navigate to={token ? "/app" : "/login"} replace />}
      />
    </Routes>
  );
}
