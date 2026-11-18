import os
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import settings  # noqa: F401  (validates DATA_SOURCE at startup)
from data_sources import DataSourceError, JobNotFoundError
from routers import glue, anomalies, alerts, history, auth, audit, auth_events, auth_anomalies, admin, security, totp, health
from routers.auth import get_current_user

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# Schema is owned by Alembic and applied by start.sh before the server boots.
# Do not call Base.metadata.create_all() here: it creates tables without RLS,
# policies, or seed data, and it cannot add columns to existing tables.

app = FastAPI(
    title="Vigil API",
    description="ETL Monitoring & Observability Platform",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(JobNotFoundError)
def _job_not_found(_: Request, exc: JobNotFoundError):
    return JSONResponse(status_code=404, content={"detail": f"Job not found: {exc}"})


@app.exception_handler(DataSourceError)
def _data_source_error(_: Request, exc: DataSourceError):
    return JSONResponse(status_code=502, content={"detail": f"Data source error: {exc}"})

_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public — no auth required
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router,  prefix="/api/v1/auth", tags=["Auth"])
app.include_router(totp.router,  prefix="/api/v1/auth", tags=["TOTP"])

# Protected — all routes require a valid Bearer token
_auth = [Depends(get_current_user)]
app.include_router(glue.router,      prefix="/api/v1/glue",      tags=["Glue"],      dependencies=_auth)
app.include_router(anomalies.router, prefix="/api/v1/anomalies", tags=["Anomalies"], dependencies=_auth)
app.include_router(alerts.router,    prefix="/api/v1/alerts",    tags=["Alerts"],    dependencies=_auth)
app.include_router(history.router,   prefix="/api/v1/history",   tags=["History"],   dependencies=_auth)
app.include_router(audit.router,      prefix="/api/v1/audit",       tags=["Audit"],       dependencies=_auth)
app.include_router(auth_events.router,    prefix="/api/v1/auth-events",    tags=["AuthEvents"],    dependencies=_auth)
app.include_router(auth_anomalies.router, prefix="/api/v1/auth-anomalies", tags=["AuthAnomalies"], dependencies=_auth)
app.include_router(admin.router,          prefix="/api/v1/admin",          tags=["Admin"],          dependencies=_auth)
app.include_router(security.router,       prefix="/api/v1/security",        tags=["Security"],       dependencies=_auth)
