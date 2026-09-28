"""FastAPI entry point. Run from the project root:  uvicorn app.main:app --reload --app-dir backend"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routes import alerts, incidents, outcomes

app = FastAPI(title="Incident Response Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    # Vite picks the next free port (5173, 5174, 5175, ...) when others are busy, so allow any local port.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(alerts.router)
app.include_router(incidents.router)
app.include_router(outcomes.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "bank": config.BANK_ID}