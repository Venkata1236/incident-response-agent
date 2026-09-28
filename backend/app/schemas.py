"""Request and response models for the API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AlertIn(BaseModel):
    title: str = Field(..., min_length=3, description="Alert headline, e.g. 'p95 latency 4.4s and 502s rising'")
    log_excerpt: str = ""
    context: str = ""
    service: str = "payments-api"
    use_memory: bool = Field(True, description="False runs the no-memory baseline for the before/after toggle")


class AvoidItem(BaseModel):
    action: str
    reason: str = ""
    incidents: list[str] = []


class Contrast(BaseModel):
    incident: str
    difference: str = ""


class Recommendation(BaseModel):
    first_action: str
    reasoning: str = ""
    avoid: list[AvoidItem] = []
    supporting_incidents: list[str] = []
    contrasting_incidents: list[Contrast] = []
    insufficient_precedent: bool = False


class RunbookStat(BaseModel):
    """Counted in code from recorded outcomes, never estimated by the LLM."""

    runbook_id: str
    title: str
    uses: int
    worked: int
    failed: int
    last_reviewed: Optional[str] = None
    days_since_review: Optional[int] = None
    flags: list[str] = []


class EvidenceCard(BaseModel):
    incident_id: str
    role: Literal["supports", "contrasts", "related"]
    date: Optional[str] = None
    summary: Optional[str] = None
    root_cause: Optional[str] = None
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    minutes_to_resolve: Optional[int] = None
    remembered_facts: list[str] = []


class AnalyzeResponse(BaseModel):
    memory_used: bool
    recommendation: Optional[Recommendation] = None
    runbook_stats: list[RunbookStat] = []
    evidence: list[EvidenceCard] = []
    latency_ms: int = 0
    warnings: list[str] = []


# ------------------------------------------------------------------ live outcomes
class StepResult(BaseModel):
    step: str = Field(..., min_length=3, description="What the engineer did, e.g. 'Roll back to the previous version'")
    runbook: Optional[str] = Field(None, pattern=r"^RB-\d{2}$", description="Runbook ID if one applies, e.g. RB-09")
    worked: bool


class OutcomeIn(BaseModel):
    """The engineer's report after an incident. This is the live write of the demo."""

    title: str = Field(..., min_length=3)
    log_excerpt: str = ""
    context: str = ""
    steps: list[StepResult] = Field(..., min_length=1)
    root_cause: str = Field(..., min_length=3)
    cause_tag: Optional[str] = Field(None, pattern=r"^[a-z0-9_]+$", description="e.g. connection_leak")
    minutes_to_resolve: Optional[int] = Field(None, ge=0)
    resolved_by: str = "on-call engineer"
    severity: str = "SEV1"
    incident_id: Optional[str] = Field(None, pattern=r"^INC-\d{3}$", description="Reuse an ID to overwrite (repeatable demo)")


class OutcomeOut(BaseModel):
    incident_id: str
    retained: bool
    memory_text: str
    note: str = "Retained. Hindsight consolidates in the background, so allow a short delay before it shows up in recall."
