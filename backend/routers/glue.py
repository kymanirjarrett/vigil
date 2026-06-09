from fastapi import APIRouter, Depends, HTTPException
from aws_client import get_glue_client
from botocore.exceptions import ClientError
from models import User
from routers.auth import get_current_user
from demo_data import get_demo_jobs, get_demo_runs

router = APIRouter()


def _use_demo(user: User) -> bool:
    return user.role == "analyst" or user.demo_mode


@router.get("/jobs")
def list_glue_jobs(current_user: User = Depends(get_current_user)):
    if _use_demo(current_user):
        jobs = get_demo_jobs()
        return {"count": len(jobs), "jobs": jobs, "source": "demo"}

    client = get_glue_client()
    try:
        response = client.get_jobs()
        jobs = [
            {
                "name": job["Name"],
                "created_on": str(job.get("CreatedOn", "")),
                "last_modified": str(job.get("LastModifiedOn", "")),
                "glue_version": job.get("GlueVersion", "N/A"),
                "worker_type": job.get("WorkerType", "N/A"),
                "max_capacity": job.get("MaxCapacity", "N/A"),
                "timeout": job.get("Timeout", "N/A"),
            }
            for job in response.get("Jobs", [])
        ]
        return {"count": len(jobs), "jobs": jobs, "source": "live"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_name}/runs")
def get_job_runs(
    job_name: str,
    max_results: int = 20,
    current_user: User = Depends(get_current_user),
):
    if _use_demo(current_user):
        runs = get_demo_runs(job_name)[:max_results]
        return {"job_name": job_name, "count": len(runs), "runs": runs, "source": "demo"}

    client = get_glue_client()
    try:
        response = client.get_job_runs(JobName=job_name, MaxResults=max_results)
        runs = [
            {
                "run_id": run["Id"],
                "status": run["JobRunState"],
                "started_on": str(run.get("StartedOn", "")),
                "completed_on": str(run.get("CompletedOn", "")),
                "execution_time": run.get("ExecutionTime", 0),
                "error_message": run.get("ErrorMessage", None),
                "dpu_seconds": run.get("DPUSeconds", None),
            }
            for run in response.get("JobRuns", [])
        ]
        return {"job_name": job_name, "count": len(runs), "runs": runs, "source": "live"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connection-test")
def test_aws_connection():
    client = get_glue_client()
    try:
        client.get_jobs(MaxResults=1)
        return {"connected": True, "service": "AWS Glue", "region": "us-east-2"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS connection failed: {str(e)}")
