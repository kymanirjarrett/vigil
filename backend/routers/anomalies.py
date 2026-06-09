from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from aws_client import get_glue_client
from botocore.exceptions import ClientError
from database import get_db
from models import AnomalyEvent, User
from routers.auth import get_current_user
from demo_data import get_demo_jobs, get_demo_runs
import statistics

router = APIRouter()


def _use_demo(user: User) -> bool:
    return user.role == "analyst" or user.demo_mode


def detect_anomalies(runs: list) -> list:
    """
    Analyze a list of job runs and flag anomalies.
    Two detection rules:
      1. Duration spike — run time is > 2 standard deviations above the mean
      2. Consecutive failures — 2 or more FAILED runs in a row
    """
    anomalies = []

    completed = [
        r for r in runs
        if r.get("execution_time") and r["status"] in ("SUCCEEDED", "FAILED")
    ]

    if len(completed) >= 3:
        times = [r["execution_time"] for r in completed]
        mean  = statistics.mean(times)
        stdev = statistics.stdev(times)
        threshold = mean + (2 * stdev)

        for run in completed:
            if run["execution_time"] > threshold and stdev > 0:
                anomalies.append({
                    "run_id":    run["run_id"],
                    "type":      "DURATION_SPIKE",
                    "severity":  "warning",
                    "message":   (
                        f"Run took {run['execution_time']}s — "
                        f"{round((run['execution_time'] - mean) / stdev, 1)}σ above average "
                        f"({round(mean)}s)"
                    ),
                    "started_on": run["started_on"],
                })

    streak = 0
    for run in runs:
        if run["status"] == "FAILED":
            streak += 1
            if streak >= 2:
                anomalies.append({
                    "run_id":    run["run_id"],
                    "type":      "CONSECUTIVE_FAILURES",
                    "severity":  "critical",
                    "message":   f"{streak} consecutive failed runs detected.",
                    "started_on": run["started_on"],
                })
                break
        else:
            streak = 0

    return anomalies


@router.get("/jobs/{job_name}/anomalies")
def get_job_anomalies(
    job_name: str,
    current_user: User = Depends(get_current_user),
):
    if _use_demo(current_user):
        runs = get_demo_runs(job_name)
        anomalies = detect_anomalies(runs)
        for a in anomalies:
            a["job_name"] = job_name
        return {
            "job_name": job_name,
            "runs_analyzed": len(runs),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "source": "demo",
        }

    client = get_glue_client()
    try:
        response = client.get_job_runs(JobName=job_name, MaxResults=50)
        runs = [
            {
                "run_id":         run["Id"],
                "status":         run["JobRunState"],
                "started_on":     str(run.get("StartedOn", "")),
                "execution_time": run.get("ExecutionTime", 0),
                "error_message":  run.get("ErrorMessage", None),
            }
            for run in response.get("JobRuns", [])
        ]
        anomalies = detect_anomalies(runs)
        return {
            "job_name": job_name,
            "runs_analyzed": len(runs),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "source": "live",
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
def get_all_anomalies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if _use_demo(current_user):
        all_anomalies = []
        for job in get_demo_jobs():
            job_name = job["name"]
            runs = get_demo_runs(job_name)
            detected = detect_anomalies(runs)
            for a in detected:
                a["job_name"] = job_name
            all_anomalies.extend(detected)
        return {
            "jobs_scanned": len(get_demo_jobs()),
            "anomaly_count": len(all_anomalies),
            "anomalies": all_anomalies,
            "source": "demo",
        }

    client = get_glue_client()
    try:
        jobs_response = client.get_jobs()
        jobs = jobs_response.get("Jobs", [])

        all_anomalies = []
        for job in jobs:
            job_name = job["Name"]
            runs_response = client.get_job_runs(JobName=job_name, MaxResults=50)
            runs = [
                {
                    "run_id":         r["Id"],
                    "status":         r["JobRunState"],
                    "started_on":     str(r.get("StartedOn", "")),
                    "execution_time": r.get("ExecutionTime", 0),
                    "error_message":  r.get("ErrorMessage", None),
                }
                for r in runs_response.get("JobRuns", [])
            ]
            detected = detect_anomalies(runs)
            for a in detected:
                a["job_name"] = job_name
            all_anomalies.extend(detected)

        for a in all_anomalies:
            record = AnomalyEvent(
                job_name=a["job_name"],
                run_id=a["run_id"],
                type=a["type"],
                severity=a["severity"],
                message=a["message"],
            )
            db.add(record)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()

        return {
            "jobs_scanned": len(jobs),
            "anomaly_count": len(all_anomalies),
            "anomalies": all_anomalies,
            "source": "live",
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
