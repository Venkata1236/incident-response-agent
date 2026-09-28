"""FastAPI entry point. Run from the project root:  uvicorn app.main:app --reload --app-dir backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routes import alerts, incidents

app = FastAPI(title="Incident Response Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(alerts.router)
app.include_router(incidents.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "bank": config.BANK_ID}
