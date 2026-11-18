from fastapi import APIRouter, Depends, Query

from data_sources import DataProvider, get_data_provider

router = APIRouter()


@router.get("/jobs")
def list_glue_jobs(provider: DataProvider = Depends(get_data_provider)):
    jobs = provider.list_jobs()
    return {"count": len(jobs), "jobs": jobs, "source": provider.name}


@router.get("/jobs/{job_name}/runs")
def get_job_runs(
    job_name: str,
    max_results: int = Query(20, ge=1, le=200),
    provider: DataProvider = Depends(get_data_provider),
):
    runs = provider.get_runs(job_name, max_results=max_results)
    return {"job_name": job_name, "count": len(runs), "runs": runs, "source": provider.name}
