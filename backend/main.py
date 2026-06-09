import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routers import glue, anomalies, alerts, history, auth, mode
from routers.auth import get_current_user
from database import engine
from models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Vigil API",
    description="ETL Monitoring & Observability Platform",
    version="1.0.0",
    lifespan=lifespan,
)

_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public — no auth required
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])

# Protected — all routes require a valid Bearer token
_auth = [Depends(get_current_user)]
app.include_router(glue.router,      prefix="/api/v1/glue",      tags=["Glue"],      dependencies=_auth)
app.include_router(anomalies.router, prefix="/api/v1/anomalies", tags=["Anomalies"], dependencies=_auth)
app.include_router(alerts.router,    prefix="/api/v1/alerts",    tags=["Alerts"],    dependencies=_auth)
app.include_router(history.router,   prefix="/api/v1/history",   tags=["History"],   dependencies=_auth)
app.include_router(mode.router,      prefix="/api/v1/mode",      tags=["Mode"],      dependencies=_auth)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Vigil API", "version": "1.0.0"}
