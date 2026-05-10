from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import glue, anomalies, alerts, history
from database import engine
from models import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Vigil API",
    description="ETL Monitoring & Observability Platform",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(glue.router,      prefix="/api/glue",      tags=["Glue"])
app.include_router(anomalies.router, prefix="/api/anomalies", tags=["Anomalies"])
app.include_router(alerts.router,    prefix="/api/alerts",    tags=["Alerts"])
app.include_router(history.router,   prefix="/api/history",   tags=["History"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Vigil API", "version": "0.4.0"}
