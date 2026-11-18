from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from anomaly_detection import detect_anomalies
from data_sources import DataProvider, get_data_provider
from database import get_db

router = APIRouter()


def _scan(provider: DataProvider, job_name: str) -> tuple[list, list]:
    runs = provider.get_runs(job_name, max_results=50)
    anomalies = detect_anomalies(runs)
    for a in anomalies:
        a["job_name"] = job_name
    return runs, anomalies


@router.get("/jobs/{job_name}/anomalies")
def get_job_anomalies(job_name: str, provider: DataProvider = Depends(get_data_provider)):
    runs, anomalies = _scan(provider, job_name)
    return {
        "job_name":      job_name,
        "runs_analyzed": len(runs),
        "anomaly_count": len(anomalies),
        "anomalies":     anomalies,
        "source":        provider.name,
    }


@router.get("/summary")
def get_all_anomalies(
    provider: DataProvider = Depends(get_data_provider),
    db: Session = Depends(get_db),
):
    jobs = provider.list_jobs()
    all_anomalies = []
    for job in jobs:
        all_anomalies.extend(_scan(provider, job["name"])[1])
    provider.record_anomalies(db, all_anomalies)
    return {
        "jobs_scanned":  len(jobs),
        "anomaly_count": len(all_anomalies),
        "anomalies":     all_anomalies,
        "source":        provider.name,
    }
