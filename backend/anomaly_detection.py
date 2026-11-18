"""Pipeline anomaly rules. Pure functions over run dicts, so they work the same
for every data source and are easy to unit test."""
import statistics

SPIKE_STDEVS     = 2  # flag runs this many standard deviations above the mean
MIN_RUNS         = 3  # need at least this many completed runs for a baseline
FAILURE_STREAK   = 2  # this many FAILED runs in a row is an incident


def detect_anomalies(runs: list) -> list:
    """
    Analyze job runs (newest first, as AWS Glue returns them) and flag anomalies:
      1. DURATION_SPIKE: run time more than 2 standard deviations above the mean
      2. CONSECUTIVE_FAILURES: 2 or more FAILED runs in a row
    """
    anomalies = []

    completed = [
        r for r in runs
        if r.get("execution_time") and r["status"] in ("SUCCEEDED", "FAILED")
    ]

    if len(completed) >= MIN_RUNS:
        times = [r["execution_time"] for r in completed]
        mean  = statistics.mean(times)
        stdev = statistics.stdev(times)
        threshold = mean + (SPIKE_STDEVS * stdev)

        for run in completed:
            if stdev > 0 and run["execution_time"] > threshold:
                anomalies.append({
                    "run_id":     run["run_id"],
                    "type":       "DURATION_SPIKE",
                    "severity":   "warning",
                    "message":    (
                        f"Run took {run['execution_time']}s, "
                        f"{round((run['execution_time'] - mean) / stdev, 1)}σ above average "
                        f"({round(mean)}s)"
                    ),
                    "started_on": run["started_on"],
                })

    streak = 0
    for run in runs:
        if run["status"] == "FAILED":
            streak += 1
            if streak >= FAILURE_STREAK:
                anomalies.append({
                    "run_id":     run["run_id"],
                    "type":       "CONSECUTIVE_FAILURES",
                    "severity":   "critical",
                    "message":    f"{streak} consecutive failed runs detected.",
                    "started_on": run["started_on"],
                })
                break
        else:
            streak = 0

    return anomalies
