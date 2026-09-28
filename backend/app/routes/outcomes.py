"""POST /outcomes: the engineer reports what worked. This is the live retain of the demo."""
from fastapi import APIRouter, HTTPException

from app.schemas import OutcomeIn, OutcomeOut
from app.services import analyzer, outcome_service
from app.services.hindsight_client import HindsightUnavailable

router = APIRouter(tags=["outcomes"])


@router.post("/outcomes", response_model=OutcomeOut)
def report_outcome(outcome: OutcomeIn) -> OutcomeOut:
    try:
        return outcome_service.record_outcome(outcome, analyzer.get_memory())
    except HindsightUnavailable as exc:
        raise HTTPException(status_code=502, detail=f"Memory write failed, nothing was saved: {exc}")
