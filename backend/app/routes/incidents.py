"""GET /incidents: past incidents for the UI history panel."""
from fastapi import APIRouter

from app.services import memory_service

router = APIRouter(tags=["incidents"])


@router.get("/incidents")
def list_incidents() -> list[dict]:
    items = memory_service.load_incidents().values()
    keys = ("incident_id", "timestamp", "severity", "symptom", "root_cause", "what_worked", "minutes_to_resolve")
    return sorted(({k: i.get(k) for k in keys} for i in items), key=lambda x: x["timestamp"], reverse=True)
