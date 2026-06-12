import { useEffect, useState } from "react";
import QRCode from "qrcode";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function BackupCodeGrid({ codes }) {
  return (
    <div style={{ marginTop: "1rem" }}>
      <p style={{ fontSize: "0.72rem", color: "var(--warn)", marginBottom: "0.6rem", fontWeight: 600 }}>
        Save these backup codes now — they will not be shown again.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.4rem" }}>
        {codes.map((c, i) => (
          <code key={i} style={{
            fontFamily:  "var(--font-mono)",
            fontSize:    "0.85rem",
            padding:     "0.35rem 0.6rem",
            background:  "rgba(0,229,160,0.06)",
            border:      "1px solid rgba(0,229,160,0.2)",
            borderRadius: "3px",
            letterSpacing: "0.08em",
            color: "var(--accent)",
          }}>{c}</code>
        ))}
      </div>
    </div>
  );
}

function EnrollFlow({ onDone }) {
  const [step, setStep]         = useState("qr");   // qr | confirm | done
  const [secret, setSecret]     = useState(null);
  const [qrUrl, setQrUrl]       = useState(null);
  const [code, setCode]         = useState("");
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(false);
  const [backupCodes, setBackupCodes] = useState([]);

  useEffect(() => {
    axios.post(`${API}/api/v1/auth/totp/enroll`)
      .then(res => {
        setSecret(res.data.secret);
        QRCode.toDataURL(res.data.uri, { width: 200, margin: 2 }).then(setQrUrl);
      })
      .catch(() => setError("Failed to start enrollment."));
  }, []);

  const handleConfirm = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/v1/auth/totp/confirm`, { code });
      setBackupCodes(res.data.backup_codes);
      setStep("done");
    } catch (err) {
      setError(err.response?.data?.detail ?? "Invalid code.");
    } finally {
      setLoading(false);
    }
  };

  if (step === "done") {
    return (
      <div>
        <p style={{ color: "var(--accent)", fontWeight: 600, marginBottom: "0.5rem" }}>
          ✓ Two-factor authentication is now active.
        </p>
        <BackupCodeGrid codes={backupCodes} />
        <button className="btn" style={{ marginTop: "1.25rem" }} onClick={onDone}>
          Done
        </button>
      </div>
    );
  }

  return (
    <div>
      {error && <div style={{ color: "var(--danger)", fontSize: "0.75rem", marginBottom: "0.75rem" }}>{error}</div>}

      {step === "qr" && (
        <div>
          <p style={{ fontSize: "0.75rem", color: "var(--text)", marginBottom: "0.75rem" }}>
            Scan with Google Authenticator, Authy, or any TOTP app.
          </p>
          {qrUrl
            ? <img src={qrUrl} alt="TOTP QR code" style={{ display: "block", width: 180, height: 180, margin: "0 auto 1rem", borderRadius: "4px", background: "#fff", padding: "6px" }} />
            : <div style={{ width: 180, height: 180, margin: "0 auto 1rem", background: "rgba(90,95,114,0.15)", borderRadius: "4px", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.7rem", color: "var(--muted)" }}>Loading QR…</div>
          }
          {secret && (
            <div style={{ textAlign: "center", marginBottom: "1rem" }}>
              <p style={{ fontSize: "0.65rem", color: "var(--muted)", marginBottom: "0.3rem" }}>Manual entry key:</p>
              <code style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", letterSpacing: "0.1em", color: "var(--text)", background: "rgba(90,95,114,0.12)", padding: "4px 8px", borderRadius: "3px" }}>
                {secret.match(/.{1,4}/g)?.join(" ")}
              </code>
            </div>
          )}
          <button className="btn" onClick={() => setStep("confirm")} disabled={!qrUrl} style={{ width: "100%" }}>
            I've scanned it →
          </button>
        </div>
      )}

      {step === "confirm" && (
        <form onSubmit={handleConfirm}>
          <p style={{ fontSize: "0.75rem", color: "var(--text)", marginBottom: "0.75rem" }}>
            Enter the 6-digit code from your app to confirm enrollment.
          </p>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            placeholder="000000"
            maxLength={6}
            value={code}
            onChange={e => setCode(e.target.value)}
            autoFocus
            style={{
              width: "100%", boxSizing: "border-box",
              background: "rgba(90,95,114,0.1)", border: "1px solid rgba(90,95,114,0.3)",
              borderRadius: "4px", color: "var(--text)", padding: "0.6rem 0.75rem",
              fontFamily: "var(--font-mono)", fontSize: "1.1rem", letterSpacing: "0.25em", textAlign: "center",
              marginBottom: "0.75rem",
            }}
          />
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button type="button" className="btn" onClick={() => setStep("qr")} style={{ flex: 1 }}>← Back</button>
            <button type="submit" className="btn" disabled={loading || code.length < 6} style={{ flex: 2 }}>
              {loading ? "Verifying…" : "Confirm"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function DisableFlow({ onDone }) {
  const [code, setCode]       = useState("");
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await axios.post(`${API}/api/v1/auth/totp/disable`, { code });
      onDone();
    } catch (err) {
      setError(err.response?.data?.detail ?? "Invalid code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <p style={{ fontSize: "0.75rem", color: "var(--text)", marginBottom: "0.75rem" }}>
        Enter your authenticator code or a backup code to confirm.
      </p>
      <input
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="000000 or XXXX-XXXX"
        value={code}
        onChange={e => setCode(e.target.value)}
        autoFocus
        style={{
          width: "100%", boxSizing: "border-box",
          background: "rgba(90,95,114,0.1)", border: "1px solid rgba(90,95,114,0.3)",
          borderRadius: "4px", color: "var(--text)", padding: "0.6rem 0.75rem",
          fontFamily: "var(--font-mono)", fontSize: "0.95rem", letterSpacing: "0.1em", textAlign: "center",
          marginBottom: "0.75rem",
        }}
      />
      {error && <div style={{ color: "var(--danger)", fontSize: "0.75rem", marginBottom: "0.6rem" }}>{error}</div>}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" className="btn" onClick={onDone} style={{ flex: 1 }}>Cancel</button>
        <button type="submit" className="btn" disabled={loading || !code} style={{ flex: 2, color: "var(--danger)", borderColor: "var(--danger)" }}>
          {loading ? "Disabling…" : "Disable 2FA"}
        </button>
      </div>
    </form>
  );
}

function RegenerateFlow({ onDone }) {
  const [code, setCode]             = useState("");
  const [error, setError]           = useState(null);
  const [loading, setLoading]       = useState(false);
  const [backupCodes, setBackupCodes] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${API}/api/v1/auth/totp/backup-codes`, { code });
      setBackupCodes(res.data.backup_codes);
    } catch (err) {
      setError(err.response?.data?.detail ?? "Invalid code.");
    } finally {
      setLoading(false);
    }
  };

  if (backupCodes) {
    return (
      <div>
        <BackupCodeGrid codes={backupCodes} />
        <button className="btn" style={{ marginTop: "1rem" }} onClick={onDone}>Done</button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <p style={{ fontSize: "0.75rem", color: "var(--text)", marginBottom: "0.75rem" }}>
        Enter your authenticator code to regenerate all backup codes. Existing codes will be invalidated.
      </p>
      <input
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="000000"
        value={code}
        onChange={e => setCode(e.target.value)}
        autoFocus
        style={{
          width: "100%", boxSizing: "border-box",
          background: "rgba(90,95,114,0.1)", border: "1px solid rgba(90,95,114,0.3)",
          borderRadius: "4px", color: "var(--text)", padding: "0.6rem 0.75rem",
          fontFamily: "var(--font-mono)", fontSize: "1.1rem", letterSpacing: "0.25em", textAlign: "center",
          marginBottom: "0.75rem",
        }}
      />
      {error && <div style={{ color: "var(--danger)", fontSize: "0.75rem", marginBottom: "0.6rem" }}>{error}</div>}
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button type="button" className="btn" onClick={onDone} style={{ flex: 1 }}>Cancel</button>
        <button type="submit" className="btn" disabled={loading || code.length < 6} style={{ flex: 2 }}>
          {loading ? "Regenerating…" : "Regenerate"}
        </button>
      </div>
    </form>
  );
}

export default function AccountPage({ user }) {
  const [totpEnabled, setTotpEnabled] = useState(user?.totp_enabled ?? false);
  const [panel, setPanel]             = useState(null); // null | "enroll" | "disable" | "regen"
  const [loading, setLoading]         = useState(true);

  useEffect(() => {
    axios.get(`${API}/api/v1/auth/totp/status`)
      .then(res => setTotpEnabled(res.data.enabled))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ maxWidth: 520 }}>
      <div className="panel" style={{ marginBottom: "1.5rem" }}>
        <div className="panel-header">
          <span className="panel-title">Account</span>
        </div>
        <div style={{ padding: "1rem 1.25rem", fontSize: "0.8rem" }}>
          <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
            <div>
              <div style={{ fontSize: "0.62rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.3rem" }}>Email</div>
              <div style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{user?.email}</div>
            </div>
            <div>
              <div style={{ fontSize: "0.62rem", color: "var(--muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.3rem" }}>Role</div>
              <span style={{
                fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px", fontWeight: 700,
                background: user?.role === "admin" ? "rgba(74,158,255,0.12)" : "rgba(90,95,114,0.15)",
                color: user?.role === "admin" ? "var(--info)" : "var(--muted)",
              }}>{user?.role}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Two-Factor Authentication</span>
          {!loading && (
            <span style={{
              fontSize: "0.62rem", padding: "2px 8px", borderRadius: "3px", fontWeight: 700,
              background: totpEnabled ? "rgba(0,229,160,0.1)" : "rgba(90,95,114,0.15)",
              color: totpEnabled ? "var(--accent)" : "var(--muted)",
            }}>
              {totpEnabled ? "ENABLED" : "DISABLED"}
            </span>
          )}
        </div>

        <div style={{ padding: "1rem 1.25rem" }}>
          {loading && <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>Loading…</div>}

          {!loading && !panel && (
            <div>
              <p style={{ fontSize: "0.75rem", color: "var(--muted)", marginBottom: "1rem", lineHeight: 1.6 }}>
                {totpEnabled
                  ? "Your account is protected with TOTP two-factor authentication."
                  : "Add an extra layer of security with a TOTP app like Google Authenticator or Authy."}
              </p>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {!totpEnabled && (
                  <button className="btn" onClick={() => setPanel("enroll")}>Enable 2FA</button>
                )}
                {totpEnabled && (
                  <>
                    <button className="btn" onClick={() => setPanel("regen")}>Regenerate backup codes</button>
                    <button
                      className="btn"
                      onClick={() => setPanel("disable")}
                      style={{ color: "var(--danger)", borderColor: "var(--danger)" }}
                    >
                      Disable 2FA
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          {!loading && panel === "enroll" && (
            <EnrollFlow onDone={() => { setTotpEnabled(true); setPanel(null); }} />
          )}

          {!loading && panel === "disable" && (
            <DisableFlow onDone={() => { setTotpEnabled(false); setPanel(null); }} />
          )}

          {!loading && panel === "regen" && (
            <RegenerateFlow onDone={() => setPanel(null)} />
          )}
        </div>
      </div>
    </div>
  );
}
