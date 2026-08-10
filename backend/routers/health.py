import os
import time

from botocore.exceptions import ClientError
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from aws_client import get_glue_client, get_s3_client
from database import SessionLocal

router = APIRouter()

_GLUE_DATABASE = os.getenv("GLUE_DATABASE_NAME", "")
_GLUE_TABLE = os.getenv("GLUE_TABLE_NAME", "vigil_sales_daily")
_ATHENA_BUCKET = os.getenv("ATHENA_RESULTS_BUCKET", "")


def _check_database() -> dict:
    t0 = time.monotonic()
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_glue() -> dict:
    try:
        get_glue_client().get_jobs(MaxResults=1)
        return {"status": "ok"}
    except ClientError as exc:
        return {"status": "error", "detail": exc.response["Error"]["Message"]}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_s3_athena_bucket() -> dict:
    if not _ATHENA_BUCKET:
        return {"status": "unconfigured", "detail": "ATHENA_RESULTS_BUCKET not set"}
    try:
        get_s3_client().head_bucket(Bucket=_ATHENA_BUCKET)
        return {"status": "ok", "bucket": _ATHENA_BUCKET}
    except ClientError as exc:
        return {"status": "error", "detail": exc.response["Error"]["Message"]}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_glue_catalog_table() -> dict:
    if not _GLUE_DATABASE:
        return {"status": "unconfigured", "detail": "GLUE_DATABASE_NAME not set"}
    try:
        get_glue_client().get_table(DatabaseName=_GLUE_DATABASE, Name=_GLUE_TABLE)
        return {"status": "ok", "database": _GLUE_DATABASE, "table": _GLUE_TABLE}
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "EntityNotFoundException":
            return {"status": "error", "detail": f"Table {_GLUE_DATABASE}.{_GLUE_TABLE} not found"}
        return {"status": "error", "detail": exc.response["Error"]["Message"]}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/health/deep")
def deep_health_check():
    checks = {
        "database": _check_database(),
        "glue": _check_glue(),
        "s3_athena_results": _check_s3_athena_bucket(),
        "glue_catalog_table": _check_glue_catalog_table(),
    }

    # database is critical — everything else can be unconfigured in local dev
    critical_failed = checks["database"]["status"] == "error"
    any_error = any(v["status"] == "error" for v in checks.values())

    overall = "healthy" if not any_error else ("degraded" if not critical_failed else "unhealthy")
    status_code = 200 if overall == "healthy" else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )
