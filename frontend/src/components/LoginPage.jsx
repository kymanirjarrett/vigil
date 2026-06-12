import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function CredentialsStep({ onSuccess }) {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/v1/auth/login`, { email, password });
      onSuccess(res.data);
    } catch (err) {
      setError(
        err.response?.status === 429
          ? "Too many login attempts, please try again later."
          : err.response?.status === 401
            ? "Invalid email or password."
            : "Could not reach the server. Is the backend running?"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="login-card" onSubmit={handleSubmit}>
      <div className="login-logo">
        <span className="logo-icon">◈</span>
        <span className="logo-text">VIGIL</span>
      </div>
      <p className="login-sub">ETL Observability Platform</p>

      <div className="login-field">
        <label className="login-label">Email</label>
        <input
          className="login-input"
          type="email"
          autoComplete="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />
      </div>

      <div className="login-field">
        <label className="login-label">Password</label>
        <input
          className="login-input"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
        />
      </div>

      {error && <div className="login-error">{error}</div>}

      <button className="login-btn" type="submit" disabled={loading}>
        {loading ? "Signing in…" : "Sign in"}
      </button>

      <p style={{ textAlign: "center", fontSize: "0.72rem", color: "var(--muted)", marginTop: "1rem" }}>
        Don't have an account?{" "}
        <Link to="/signup" style={{ color: "var(--accent)", textDecoration: "none" }}>
          Sign up
        </Link>
      </p>
    </form>
  );
}

function TotpStep({ tempToken, onSuccess, onBack }) {
  const [code, setCode]       = useState("");
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/v1/auth/totp/verify-login`, {
        temp_token: tempToken,
        code,
      });
      onSuccess(res.data);
    } catch (err) {
      setError(
        err.response?.status === 401
          ? "Invalid code. Try again or use a backup code."
          : "Could not reach the server."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="login-card" onSubmit={handleSubmit}>
      <div className="login-logo">
        <span className="logo-icon">◈</span>
        <span className="logo-text">VIGIL</span>
      </div>
      <p className="login-sub" style={{ marginBottom: "0.25rem" }}>Two-Factor Authentication</p>
      <p style={{ fontSize: "0.72rem", color: "var(--muted)", textAlign: "center", marginBottom: "1.25rem" }}>
        Enter the 6-digit code from your authenticator app,<br />or a backup code (format: XXXX-XXXX).
      </p>

      <div className="login-field">
        <label className="login-label">Code</label>
        <input
          className="login-input"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          value={code}
          onChange={e => setCode(e.target.value)}
          maxLength={9}
          required
          autoFocus
          style={{ letterSpacing: "0.2em", textAlign: "center", fontSize: "1.1rem" }}
        />
      </div>

      {error && <div className="login-error">{error}</div>}

      <button className="login-btn" type="submit" disabled={loading || !code}>
        {loading ? "Verifying…" : "Verify"}
      </button>

      <button
        type="button"
        onClick={onBack}
        style={{ background: "none", border: "none", color: "var(--muted)", fontSize: "0.72rem", cursor: "pointer", marginTop: "0.75rem", width: "100%", textAlign: "center" }}
      >
        ← Back to login
      </button>
    </form>
  );
}

export default function LoginPage({ onLogin }) {
  const [tempToken, setTempToken] = useState(null);

  const handleCredentials = (data) => {
    if (data.requires_2fa) {
      setTempToken(data.temp_token);
    } else {
      onLogin(data.access_token, data.user, data.refresh_token);
    }
  };

  const handleTotp = (data) => {
    onLogin(data.access_token, data.user, data.refresh_token);
  };

  return (
    <div className="login-backdrop">
      {tempToken
        ? <TotpStep tempToken={tempToken} onSuccess={handleTotp} onBack={() => setTempToken(null)} />
        : <CredentialsStep onSuccess={handleCredentials} />
      }
    </div>
  );
}
