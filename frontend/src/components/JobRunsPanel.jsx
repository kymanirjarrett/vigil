import { useEffect, useState } from "react";
import axios from "axios";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const STATUS_COLOR = {
  SUCCEEDED: "var(--accent)",
  RUNNING: "var(--info)",
  FAILED: "var(--danger)",
  STOPPED: "var(--muted)",
};

function StatusBadge({ status }) {
  const cls = status?.toLowerCase() ?? "stopped";
  return (
    <span className={`badge ${cls}`}>
      <span className="badge-dot" />
      {status ?? "UNKNOWN"}
    </span>
  );
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border2)",
        padding: "10px 14px",
        borderRadius: 4,
        fontSize: "0.75rem",
      }}
    >
      <div style={{ color: "var(--muted)", marginBottom: 4 }}>
        Run ID: {d.run_id?.slice(0, 16)}…
      </div>
      <div>
        Status:{" "}
        <span style={{ color: STATUS_COLOR[d.status] ?? "var(--muted)" }}>
          {d.status}
        </span>
      </div>
      <div>
        Duration:{" "}
        <span style={{ color: "var(--text)" }}>{d.execution_time}s</span>
      </div>
    </div>
  );
};

export default function JobRunsPanel({ jobName, onClose }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await axios.get(`${API}/api/glue/jobs/${jobName}/runs`);
        setRuns(res.data.runs);
      } catch {
        setError("Could not load run history.");
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [jobName]);

  const succeeded = runs.filter((r) => r.status === "SUCCEEDED").length;
  const failed = runs.filter((r) => r.status === "FAILED").length;
  const avgTime = runs.length
    ? Math.round(
        runs.reduce((a, r) => a + (r.execution_time || 0), 0) / runs.length,
      )
    : 0;

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Run History — {jobName}</span>
        <button className="btn btn-close" onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Stats row */}
      {!loading && !error && (
        <div className="runs-meta">
          <div className="meta-item">
            <span className="meta-label">Total Runs</span>
            <span className="meta-value">{runs.length}</span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Succeeded</span>
            <span className="meta-value" style={{ color: "var(--accent)" }}>
              {succeeded}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Failed</span>
            <span className="meta-value" style={{ color: "var(--danger)" }}>
              {failed}
            </span>
          </div>
          <div className="meta-item">
            <span className="meta-label">Avg Duration</span>
            <span className="meta-value">{avgTime}s</span>
          </div>
        </div>
      )}

      {/* Chart */}
      {!loading && !error && runs.length > 0 && (
        <div
          style={{
            padding: "1.25rem",
            borderBottom: "1px solid var(--border)",
          }}
        >
          <div
            style={{
              fontSize: "0.65rem",
              color: "var(--muted)",
              marginBottom: "0.75rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Execution Time per Run (seconds)
          </div>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={[...runs].reverse()} barSize={18}>
              <XAxis dataKey="run_id" hide />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--muted)" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ fill: "rgba(255,255,255,0.03)" }}
              />
              <Bar dataKey="execution_time" radius={[3, 3, 0, 0]}>
                {runs.map((r, i) => (
                  <Cell
                    key={i}
                    fill={STATUS_COLOR[r.status] ?? "var(--muted)"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Runs table */}
      <div className="table-wrap">
        {loading && <div className="state-msg">Loading runs...</div>}
        {error && (
          <div className="state-msg" style={{ color: "var(--danger)" }}>
            {error}
          </div>
        )}
        {!loading && !error && runs.length === 0 && (
          <div className="state-msg">No runs found for this job yet.</div>
        )}
        {!loading && !error && runs.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Status</th>
                <th>Started</th>
                <th>Duration</th>
                <th>DPU Seconds</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: "var(--muted)",
                    }}
                  >
                    {run.run_id.slice(0, 20)}…
                  </td>
                  <td>
                    <StatusBadge status={run.status} />
                  </td>
                  <td>
                    {run.started_on
                      ? new Date(run.started_on).toLocaleString()
                      : "—"}
                  </td>
                  <td>{run.execution_time ?? "—"}s</td>
                  <td>{run.dpu_seconds ?? "—"}</td>
                  <td
                    style={{
                      color: "var(--danger)",
                      fontSize: "0.72rem",
                      maxWidth: 200,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {run.error_message ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
