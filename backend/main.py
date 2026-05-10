from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routers import glue, anomalies, alerts, history, auth
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
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public — no auth required
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# Protected — all routes require a valid Bearer token
_auth = [Depends(get_current_user)]
app.include_router(glue.router,      prefix="/api/glue",      tags=["Glue"],      dependencies=_auth)
app.include_router(anomalies.router, prefix="/api/anomalies", tags=["Anomalies"], dependencies=_auth)
app.include_router(alerts.router,    prefix="/api/alerts",    tags=["Alerts"],    dependencies=_auth)
app.include_router(history.router,   prefix="/api/history",   tags=["History"],   dependencies=_auth)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Vigil API", "version": "0.5.0"}
