from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import glue

app = FastAPI(
    title="Vigil API",
    description="ETL Monitoring & Observability Platform",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(glue.router, prefix="/api/glue", tags=["Glue"])

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Vigil API"}
