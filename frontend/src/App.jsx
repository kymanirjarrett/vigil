import { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import axios from "axios";
import LandingPage from "./components/LandingPage";
import LoginPage from "./components/LoginPage";
import SignupPage from "./components/SignupPage";
import AppShell from "./components/AppShell";
import DashboardView from "./components/DashboardView";
import AuditLogPage from "./components/AuditLogPage";
import SecurityEventsPage from "./components/SecurityEventsPage";
import ThreatDetectionPage from "./components/ThreatDetectionPage";
import "./App.css";

const _stored = localStorage.getItem("vigil_token");
const _storedUser = (() => {
  try { return JSON.parse(localStorage.getItem("vigil_user")); } catch { return null; }
})();

if (_stored) axios.defaults.headers.common["Authorization"] = `Bearer ${_stored}`;

function AuditRoute() {
  return (
    <>
      <div className="page-title">
        <h1>Audit Log</h1>
        <p>Immutable record of all user actions — append-only</p>
      </div>
      <AuditLogPage />
    </>
  );
}

function SecurityRoute() {
  return (
    <>
      <div className="page-title">
        <h1>Security Events</h1>
        <p>Authentication event stream — all login attempts, successes, and signups</p>
      </div>
      <SecurityEventsPage />
    </>
  );
}

function ThreatDetectionRoute() {
  return (
    <>
      <div className="page-title">
        <h1>Threat Detection</h1>
        <p>Live scan for brute-force and credential-stuffing attacks in auth event history</p>
      </div>
      <ThreatDetectionPage />
    </>
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
    navigate("/app/dashboard");
  };

  const handleLogout = () => {
    delete axios.defaults.headers.common["Authorization"];
    localStorage.removeItem("vigil_token");
    localStorage.removeItem("vigil_user");
    setToken(null);
    setUser(null);
    navigate("/");
  };

  const handleUserUpdate = (updatedUser) => {
    localStorage.setItem("vigil_user", JSON.stringify(updatedUser));
    setUser(updatedUser);
  };

  return (
    <Routes>
      <Route
        path="/"
        element={token ? <Navigate to="/app/dashboard" replace /> : <LandingPage />}
      />
      <Route
        path="/login"
        element={token ? <Navigate to="/app/dashboard" replace /> : <LoginPage onLogin={handleLogin} />}
      />
      <Route
        path="/signup"
        element={token ? <Navigate to="/app/dashboard" replace /> : <SignupPage onLogin={handleLogin} />}
      />

      <Route
        path="/app"
        element={
          token
            ? <AppShell user={user} onLogout={handleLogout} onUserUpdate={handleUserUpdate} />
            : <Navigate to="/" replace />
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DashboardView />} />
        <Route
          path="audit"
          element={user?.role === "admin" ? <AuditRoute /> : <Navigate to="/app/dashboard" replace />}
        />
        <Route
          path="security"
          element={user?.role === "admin" ? <SecurityRoute /> : <Navigate to="/app/dashboard" replace />}
        />
        <Route
          path="threats"
          element={user?.role === "admin" ? <ThreatDetectionRoute /> : <Navigate to="/app/dashboard" replace />}
        />
      </Route>

      <Route
        path="*"
        element={<Navigate to={token ? "/app/dashboard" : "/"} replace />}
      />
    </Routes>
  );
}
