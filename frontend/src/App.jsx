import { useState, useEffect, useRef } from "react";
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
import SecurityPosturePage from "./components/SecurityPosturePage";
import SessionsPage from "./components/SessionsPage";
import AdminUsersPage from "./components/AdminUsersPage";
import "./App.css";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const _stored     = localStorage.getItem("vigil_token");
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

function SecurityPostureRoute() {
  return (
    <>
      <div className="page-title">
        <h1>Security Posture</h1>
        <p>Aggregated security metrics — login activity, anomalies, and recent events</p>
      </div>
      <SecurityPosturePage />
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

function AdminUsersRoute({ user }) {
  return (
    <>
      <div className="page-title">
        <h1>User Management</h1>
        <p>Manage roles, lockouts, and sessions for all accounts</p>
      </div>
      <AdminUsersPage currentUserId={user?.id} />
    </>
  );
}

function SessionsRoute() {
  return (
    <>
      <div className="page-title">
        <h1>Sessions</h1>
        <p>Your active login sessions — revoke any device at any time</p>
      </div>
      <SessionsPage />
    </>
  );
}

export default function App() {
  const [token, setToken] = useState(_stored);
  const [user, setUser]   = useState(_storedUser);
  const navigate          = useNavigate();

  // Refs used inside the interceptor closure to avoid stale captures
  const isRefreshing  = useRef(false);
  const failedQueue   = useRef([]);

  const processQueue = (err, newToken = null) => {
    failedQueue.current.forEach(({ resolve, reject }) => {
      if (err) reject(err);
      else resolve(newToken);
    });
    failedQueue.current = [];
  };

  const doLogout = () => {
    delete axios.defaults.headers.common["Authorization"];
    localStorage.removeItem("vigil_token");
    localStorage.removeItem("vigil_refresh_token");
    localStorage.removeItem("vigil_user");
    setToken(null);
    setUser(null);
    navigate("/login");
  };

  useEffect(() => {
    const id = axios.interceptors.response.use(
      res => res,
      async err => {
        const original = err.config;

        // Only attempt refresh on 401s that haven't already been retried
        // and are not from the refresh endpoint itself (avoid infinite loop)
        if (
          err.response?.status === 401 &&
          !original._retry &&
          !original.url?.includes("/auth/refresh")
        ) {
          const storedRefresh = localStorage.getItem("vigil_refresh_token");
          if (!storedRefresh) {
            doLogout();
            return Promise.reject(err);
          }

          if (isRefreshing.current) {
            // Queue this request until the in-flight refresh resolves
            return new Promise((resolve, reject) => {
              failedQueue.current.push({ resolve, reject });
            }).then(newToken => {
              original.headers["Authorization"] = `Bearer ${newToken}`;
              return axios(original);
            });
          }

          original._retry       = true;
          isRefreshing.current  = true;

          try {
            const res = await axios.post(`${API}/api/v1/auth/refresh`, {
              refresh_token: storedRefresh,
            });
            const { access_token, refresh_token: newRefresh } = res.data;

            localStorage.setItem("vigil_token", access_token);
            localStorage.setItem("vigil_refresh_token", newRefresh);
            axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
            setToken(access_token);

            processQueue(null, access_token);
            original.headers["Authorization"] = `Bearer ${access_token}`;
            return axios(original);
          } catch (refreshErr) {
            processQueue(refreshErr, null);
            doLogout();
            return Promise.reject(refreshErr);
          } finally {
            isRefreshing.current = false;
          }
        }

        return Promise.reject(err);
      }
    );
    return () => axios.interceptors.response.eject(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  const handleLogin = (newToken, userData, refreshToken) => {
    axios.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
    localStorage.setItem("vigil_token", newToken);
    if (refreshToken) localStorage.setItem("vigil_refresh_token", refreshToken);
    if (userData)     localStorage.setItem("vigil_user", JSON.stringify(userData));
    setToken(newToken);
    setUser(userData);
    navigate("/app/dashboard");
  };

  const handleLogout = () => {
    // Best-effort server-side revocation; don't wait for it
    axios.post(`${API}/api/v1/auth/logout`).catch(() => {});
    doLogout();
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
        <Route path="sessions"  element={<SessionsRoute />} />
        <Route
          path="admin/users"
          element={user?.role === "admin" ? <AdminUsersRoute user={user} /> : <Navigate to="/app/dashboard" replace />}
        />
        <Route
          path="posture"
          element={user?.role === "admin" ? <SecurityPostureRoute /> : <Navigate to="/app/dashboard" replace />}
        />
        <Route
          path="threats"
          element={user?.role === "admin" ? <ThreatDetectionRoute /> : <Navigate to="/app/dashboard" replace />}
        />
        <Route
          path="security"
          element={user?.role === "admin" ? <SecurityRoute /> : <Navigate to="/app/dashboard" replace />}
        />
        <Route
          path="audit"
          element={user?.role === "admin" ? <AuditRoute /> : <Navigate to="/app/dashboard" replace />}
        />
      </Route>

      <Route
        path="*"
        element={<Navigate to={token ? "/app/dashboard" : "/"} replace />}
      />
    </Routes>
  );
}
