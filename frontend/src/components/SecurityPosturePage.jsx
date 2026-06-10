import { useEffect, useState } from "react";
import axios from "axios";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const ACTION_COLORS = {
  "user.locked":   "var(--danger)",
  "user.unlocked": "var(--accent)",
  "user.login":    "var(--muted)",
  "user.signup":   "var(--info)",
};

function MetricCard({ label, value, color, sub }) {
  return (
    <div className="panel" style={{ flex: 1, padding: "1rem 1.25rem", minWidth: 140 }}>
      <div style={{
        fontSize: "0.62rem", color: "var(--muted)",
        letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "0.4rem",
      }}>
        {label}
      </div>
      <div style={{
        fontSize: "1.75rem", fontWeight: 700,
        color: color ?? "var(--text)", fontFamily: "var(--font-mono)",
        lineHeight: 1,
      }}>
        {value ?? "—"}
      </div>
      {sub && (
        <div style={{ fontSize: "0.62rem", color: "var(--muted)", marginTop: "0.35rem" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

const CHART_STYLE = {
  background: "transparent",
  fontSize: "0.65rem",
  fontFamily: "var(--font-mono)",
};

const TOOLTIP_STYLE = {
  backgroundColor: "#111318",
  border: "1px solid #2a2d38",
  borderRadius: 4,
  fontSize: "0.7rem",
  fontFamily: "DM Mono, monospace",
};

export default function SecurityPosturePage() {
  const [data, setData]   = useState(null);
  const [error, setError] = useState(null);
  const [tick, setTick]   = useState(0);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/api/v1/security/posture`)
      .then(res => { if (!cancelled) { setError(null); setData(res.data); } })
      .catch(() => { if (!cancelled) setError("Failed to load security posture."); });
    return () => { cancelled = true; };
  }, [tick]);

  const loading = data === null && !error;

  const anomaly    = data?.anomaly_summary ?? {};
  const failures   = data?.failures_24h    ?? 0;
  const locked     = data?.locked_count    ?? 0;
  const totalUsers = (data?.users_by_role ?? []).reduce((s, r) => s + r.count, 0);

  return (
    <div>
      {/* ── Summary cards ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <MetricCard
          label="Critical Threats"
          value={loading ? "—" : anomaly.critical ?? 0}
          color={(anomaly.critical ?? 0) > 0 ? "var(--danger)" : "var(--muted)"}
          sub="last 24h"
        />
        <MetricCard
          label="Warnings"
          value={loading ? "—" : anomaly.warning ?? 0}
          color={(anomaly.warning ?? 0) > 0 ? "var(--warn)" : "var(--muted)"}
          sub="last 24h"
        />
        <MetricCard
          label="Login Failures"
          value={loading ? "—" : failures}
          color={failures > 10 ? "var(--danger)" : failures > 0 ? "var(--warn)" : "var(--muted)"}
          sub="last 24h"
        />
        <MetricCard
          label="Locked Accounts"
          value={loading ? "—" : locked}
          color={locked > 0 ? "var(--warn)" : "var(--muted)"}
        />
        <MetricCard
          label="Active Users"
          value={loading ? "—" : totalUsers}
          color="var(--text)"
        />
      </div>

      {error && (
        <div className="panel" style={{ padding: "1.5rem", color: "var(--danger)", textAlign: "center" }}>
          {error}
        </div>
      )}

      {/* ── Login activity line chart ────────────────────────────────────── */}
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <div className="panel-header">
          <span className="panel-title">Login Activity — Last 24h</span>
          <button className="btn" onClick={() => { setData(null); setTick(t => t + 1); }}>
            ↻ Refresh
          </button>
        </div>
        <div style={{ padding: "1rem 0.5rem 0.5rem" }}>
          {loading ? (
            <div className="state-msg">Loading...</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={data?.login_activity ?? []} style={CHART_STYLE}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" />
                <XAxis
                  dataKey="hour"
                  tick={{ fill: "#5a5f72", fontSize: 10 }}
                  tickLine={false}
                  interval={3}
                />
                <YAxis tick={{ fill: "#5a5f72", fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend
                  wrapperStyle={{ fontSize: "0.7rem", paddingTop: "0.5rem" }}
                  formatter={v => v.charAt(0).toUpperCase() + v.slice(1)}
                />
                <Line
                  type="monotone" dataKey="successes"
                  stroke="#00e5a0" strokeWidth={2} dot={false} name="successes"
                />
                <Line
                  type="monotone" dataKey="failures"
                  stroke="#ff4757" strokeWidth={2} dot={false} name="failures"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── Bottom row: Top IPs + Users by Role ─────────────────────────── */}
      <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>

        {/* Top source IPs */}
        <div className="panel" style={{ flex: "1 1 340px" }}>
          <div className="panel-header">
            <span className="panel-title">Top Source IPs — Failures (24h)</span>
          </div>
          <div className="table-wrap">
            {loading ? (
              <div className="state-msg">Loading...</div>
            ) : !data?.top_ips?.length ? (
              <div className="state-msg">No failures recorded.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th style={{ textAlign: "right" }}>Failures</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_ips.map((row, i) => (
                    <tr key={i}>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                        {row.ip}
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <span style={{
                          fontFamily: "var(--font-mono)", fontWeight: 700,
                          color: row.failure_count >= 10 ? "var(--danger)" : "var(--warn)",
                        }}>
                          {row.failure_count}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Users by role */}
        <div className="panel" style={{ flex: "1 1 280px" }}>
          <div className="panel-header">
            <span className="panel-title">Users by Role</span>
          </div>
          <div style={{ padding: "1rem 0.5rem 0.5rem" }}>
            {loading ? (
              <div className="state-msg">Loading...</div>
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart
                  data={data?.users_by_role ?? []}
                  style={CHART_STYLE}
                  barSize={32}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2028" vertical={false} />
                  <XAxis dataKey="role" tick={{ fill: "#5a5f72", fontSize: 11 }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: "#5a5f72", fontSize: 10 }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="count" name="users" fill="#4a9eff" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* ── Recent security events ───────────────────────────────────────── */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Recent Security Events</span>
          {data?.source && (
            <span style={{ fontSize: "0.65rem", color: data.source === "live" ? "var(--accent)" : "var(--warn)" }}>
              {data.source}
            </span>
          )}
        </div>
        <div className="table-wrap">
          {loading ? (
            <div className="state-msg">Loading...</div>
          ) : !data?.security_events?.length ? (
            <div className="state-msg">No security events in the last 7 days.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Subject</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {data.security_events.map((e, i) => (
                  <tr key={i}>
                    <td style={{ color: "var(--muted)", fontSize: "0.72rem", whiteSpace: "nowrap" }}>
                      {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                    </td>
                    <td>
                      <span style={{
                        fontSize: "0.65rem", padding: "2px 7px", borderRadius: "3px",
                        fontWeight: 600,
                        color: ACTION_COLORS[e.action] ?? "var(--muted)",
                        background: "rgba(255,255,255,0.04)",
                      }}>
                        {e.action}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                      {e.resource_id ?? "—"}
                    </td>
                    <td style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--muted)" }}>
                      {e.ip_address ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
