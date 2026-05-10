import { useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      // FastAPI OAuth2PasswordRequestForm expects form-encoded body
      const params = new URLSearchParams();
      params.append("username", username);
      params.append("password", password);
      const res = await axios.post(`${API}/api/auth/login`, params);
      onLogin(res.data.access_token);
    } catch (err) {
      setError(
        err.response?.status === 401
          ? "Invalid username or password."
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
          <label className="login-label">Username</label>
          <input
            className="login-input"
            type="text"
            autoComplete="username"
            value={username}
            onChange={e => setUsername(e.target.value)}
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

        {error && (
          <div className="login-error">{error}</div>
        )}

        <button className="login-btn" type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
