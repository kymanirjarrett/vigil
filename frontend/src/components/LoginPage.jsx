import { useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function LoginPage({ onLogin }) {
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
      onLogin(res.data.access_token, res.data.user, res.data.refresh_token);
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
    <div className="login-backdrop">
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
    </div>
  );
}
