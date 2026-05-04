from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import glue, anomalies, alerts

app = FastAPI(
    title="Vigil API",
    description="ETL Monitoring & Observability Platform",
    version="0.3.0"
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

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Vigil API", "version": "0.3.0"}
