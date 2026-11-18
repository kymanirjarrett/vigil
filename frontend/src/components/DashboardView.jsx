import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import JobsTable from "./JobsTable";
import JobRunsPanel from "./JobRunsPanel";
import AnomalyBanner from "./AnomalyBanner";
import AlertsPanel from "./AlertsPanel";
import HistoryPanel from "./HistoryPanel";

export default function DashboardView() {
  const { user } = useOutletContext();
  const [selectedJob, setSelectedJob] = useState(null);

  return (
    <>
      <div className="page-title">
        <h1>Glue Job Monitor</h1>
        <p>Select a job to inspect its run history</p>
      </div>

      <AnomalyBanner />
      <JobsTable
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
