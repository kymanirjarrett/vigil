import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

import settings
from data_sources import DataProvider, get_data_provider
from database import SessionLocal

router = APIRouter()


def _check_database() -> dict:
    # A real query: this is what resets Supabase's inactivity timer.
    t0 = time.monotonic()
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "Vigil API", "version": "1.0.0",
            "data_source": settings.DATA_SOURCE}


@router.get("/health/deep")
def deep_health_check(provider: DataProvider = Depends(get_data_provider)):
    checks = {"database": _check_database(), **provider.health_checks()}

    # The database is critical. Other dependencies can only degrade the
    # status; "skipped" and "unconfigured" checks do not count against it.
    if checks["database"]["status"] == "error":
        overall = "unhealthy"
    elif any(c["status"] == "error" for c in checks.values()):
        overall = "degraded"
    else:
        overall = "healthy"

    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={"status": overall, "data_source": settings.DATA_SOURCE, "checks": checks},
    )
