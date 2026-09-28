"""POST /analyze: analyze an alert with memory on or off.

Plain `def` (not async) on purpose: the Hindsight client runs its own event loop internally,
and FastAPI runs sync handlers in a worker thread, which avoids a nested-loop clash.
"""
from fastapi import APIRouter

from app.schemas import AlertIn, AnalyzeResponse
from app.services import analyzer

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_alert(alert: AlertIn) -> AnalyzeResponse:
    return analyzer.analyze(alert)
