import { useEffect, useState } from "react";
import axios from "axios";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function JobsTable({ onSelectJob, selectedJob }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadJobs = async () => {
    try {
      const res = await axios.get(`${API}/api/glue/jobs`);
      return res.data.jobs;
    } catch {
      throw new Error("Failed to load jobs. Is the backend running?");
    }
  };

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);

    try {
      const jobsData = await loadJobs();
      setJobs(jobsData);
    } catch {
      setError("Failed to load jobs. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const jobsData = await loadJobs();
        if (!cancelled) {
          setJobs(jobsData);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load jobs. Is the backend running?");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Glue Jobs — {jobs.length} found</span>
        <button className="btn" onClick={fetchJobs}>
          ↻ Refresh
        </button>
      </div>

      <div className="table-wrap">
        {loading && <div className="state-msg">Loading jobs...</div>}
        {error && (
          <div className="state-msg" style={{ color: "var(--danger)" }}>
            {error}
          </div>
        )}
        {!loading && !error && jobs.length === 0 && (
          <div className="state-msg">No Glue jobs found in us-east-2.</div>
        )}
        {!loading && !error && jobs.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Job Name</th>
                <th>Glue Version</th>
                <th>Worker Type</th>
                <th>Last Modified</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr
                  key={job.name}
                  className={selectedJob === job.name ? "selected" : ""}
                  onClick={() => onSelectJob(job.name)}
                >
                  <td>{job.name}</td>
                  <td>{job.glue_version}</td>
                  <td>{job.worker_type}</td>
                  <td>
                    {job.last_modified
                      ? new Date(job.last_modified).toLocaleString()
                      : "—"}
                  </td>
                  <td>
                    <span
                      style={{ fontSize: "0.7rem", color: "var(--accent)" }}
                    >
                      View runs →
                    </span>
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
