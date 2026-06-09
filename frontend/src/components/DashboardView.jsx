import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import JobsTable from "./JobsTable";
import JobRunsPanel from "./JobRunsPanel";
import AnomalyBanner from "./AnomalyBanner";
import AlertsPanel from "./AlertsPanel";
import HistoryPanel from "./HistoryPanel";

export default function DashboardView() {
  const { user, modeKey } = useOutletContext();
  const [selectedJob, setSelectedJob] = useState(null);

  const isDemo = user?.role === "analyst" || user?.demo_mode;

  return (
    <>
      <div className="page-title">
        <h1>Glue Job Monitor</h1>
        <p>
          {isDemo
            ? "Viewing synthetic demo data — anomalies are pre-engineered for demonstration"
            : "Select a job to inspect its run history"}
        </p>
      </div>

      <AnomalyBanner key={`anomaly-${modeKey}`} />
      <JobsTable
        key={`jobs-${modeKey}`}
        onSelectJob={setSelectedJob}
        selectedJob={selectedJob}
      />

      {selectedJob && (
        <>
          <JobRunsPanel jobName={selectedJob} onClose={() => setSelectedJob(null)} />
          <AlertsPanel jobName={selectedJob} user={user} />
        </>
      )}

      <HistoryPanel />
    </>
  );
}
