import { useState, useEffect } from "react";
import axios from "axios";
import LoginPage from "./components/LoginPage";
import JobsTable from "./components/JobsTable";
import JobRunsPanel from "./components/JobRunsPanel";
import AnomalyBanner from "./components/AnomalyBanner";
import AlertsPanel from "./components/AlertsPanel";
import HistoryPanel from "./components/HistoryPanel";
import "./App.css";

// Set header immediately at module load so any stored token is ready
// before the first component render fires API calls.
const _stored = localStorage.getItem("vigil_token");
if (_stored) axios.defaults.headers.common["Authorization"] = `Bearer ${_stored}`;

export default function App() {
  const [token, setToken]             = useState(_stored);
  const [selectedJob, setSelectedJob] = useState(null);

  // Intercept 401s globally — clear token and fall back to login
  useEffect(() => {
    const id = axios.interceptors.response.use(
      res => res,
      err => {
        if (err.response?.status === 401) {
          delete axios.defaults.headers.common["Authorization"];
          localStorage.removeItem("vigil_token");
          setToken(null);
        }
        return Promise.reject(err);
      }
    );
    return () => axios.interceptors.response.eject(id);
  }, []);

  const handleLogin = (newToken) => {
    // Set header synchronously before state update so the first
    // re-render's API calls already carry the token.
    axios.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
    localStorage.setItem("vigil_token", newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    delete axios.defaults.headers.common["Authorization"];
    localStorage.removeItem("vigil_token");
    setToken(null);
    setSelectedJob(null);
  };

  if (!token) return <LoginPage onLogin={handleLogin} />;

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
          <button className="btn" onClick={handleLogout} style={{ fontSize: "0.68rem" }}>
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
