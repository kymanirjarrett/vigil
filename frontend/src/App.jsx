import { useState } from "react";
import JobsTable from "./components/JobsTable";
import JobRunsPanel from "./components/JobRunsPanel";
import AnomalyBanner from "./components/AnomalyBanner";
import AlertsPanel from "./components/AlertsPanel";
import "./App.css";

export default function App() {
  const [selectedJob, setSelectedJob] = useState(null);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">VIGIL</span>
          </div>
          <span className="logo-sub">ETL Observability Platform</span>
        </div>
        <div className="header-right">
          <div className="status-indicator">
            <span className="pulse" />
            <span className="status-text">LIVE</span>
          </div>
          <span className="region-badge">us-east-2</span>
        </div>
      </header>

      <main className="main">
        <div className="page-title">
          <h1>Glue Job Monitor</h1>
          <p>Select a job to inspect its run history</p>
        </div>

        <AnomalyBanner />
        <JobsTable onSelectJob={setSelectedJob} selectedJob={selectedJob} />

        {selectedJob && (
          <>
            <JobRunsPanel jobName={selectedJob} onClose={() => setSelectedJob(null)} />
            <AlertsPanel jobName={selectedJob} />
          </>
        )}
      </main>
    </div>
  );
}
