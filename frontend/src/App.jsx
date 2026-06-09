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
import "./App.css";

const _stored = localStorage.getItem("vigil_token");
const _storedUser = (() => {
  try { return JSON.parse(localStorage.getItem("vigil_user")); } catch { return null; }
})();

if (_stored) axios.defaults.headers.common["Authorization"] = `Bearer ${_stored}`;

function Dashboard({ onLogout, user }) {
  const [selectedJob, setSelectedJob] = useState(null);

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
          <div className="status-indicator">
            <span className="pulse" />
            <span className="status-text">LIVE</span>
          </div>
          <span className="region-badge">us-east-2</span>
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
          <button className="btn" onClick={onLogout} style={{ fontSize: "0.68rem" }}>
            Sign out
          </button>
        </div>
      </header>

      <main className="main">
        <div className="page-title">
          <h1>Glue Job Monitor</h1>
          <p>Select a job to inspect its run history</p>
        </div>

        <AnomalyBanner />
        <JobsTable onSelectJob={setSelectedJob} selectedJob={selectedJob} />

        {selectedJob && (
          <>
            <JobRunsPanel jobName={selectedJob} onClose={() => setSelectedJob(null)} />
            <AlertsPanel jobName={selectedJob} />
          </>
        )}

        <HistoryPanel />
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
        element={token ? <Dashboard onLogout={handleLogout} user={user} /> : <Navigate to="/login" replace />}
      />
      <Route
        path="*"
        element={<Navigate to={token ? "/app" : "/login"} replace />}
      />
    </Routes>
  );
}
