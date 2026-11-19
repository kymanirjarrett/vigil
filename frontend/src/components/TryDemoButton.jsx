import { useState } from "react";
import axios from "axios";
import { API } from "../api";

/**
 * One click: get tokens for the shared read-only guest account and hand them
 * to onLogin, which stores them and navigates to the dashboard.
 */
export default function TryDemoButton({ onLogin, className, children = "Try the demo" }) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const start = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/v1/auth/guest`);
      onLogin(res.data.access_token, res.data.user, res.data.refresh_token);
    } catch (err) {
      setError(
        err.response?.status === 429
          ? "Too many demo sessions from this network. Try again in a minute."
          : "Could not start the demo. The server may be waking up; try again in a moment."
      );
      setLoading(false);
    }
  };

  return (
    <>
      <button type="button" className={className} onClick={start} disabled={loading}>
        {loading ? "Starting demo…" : children}
      </button>
      {error && <span className="try-demo-error" role="alert">{error}</span>}
    </>
  );
}
