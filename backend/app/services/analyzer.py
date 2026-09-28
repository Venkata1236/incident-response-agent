"""Turns an alert into a recommendation.

memory ON : recall (fast evidence) -> reflect (reasoning with structured output) -> deterministic stats
memory OFF: baseline LLM that sees only the alert and the runbooks

Failure policy: never crash the request. If reflect fails, fall back to recall-only evidence with a
visible warning. If Hindsight is down entirely, say so.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from app import config
from app.schemas import AlertIn, AnalyzeResponse, Contrast, Recommendation
from app.services import llm, memory_service
from app.services.hindsight_client import HindsightMemory, HindsightUnavailable

log = logging.getLogger(__name__)

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "analyze_alert.txt").read_text(encoding="utf-8")

# Flat, inline schema (no $ref) so it is accepted by Hindsight's response_schema.
REFLECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "first_action": {"type": "string"},
        "reasoning": {"type": "string"},
        "avoid": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "reason": {"type": "string"},
                    "incidents": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["action"],
            },
        },
        "supporting_incidents": {"type": "array", "items": {"type": "string"}},
        "contrasting_incidents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"incident": {"type": "string"}, "difference": {"type": "string"}},
                "required": ["incident"],
            },
        },
        "insufficient_precedent": {"type": "boolean"},
    },
    "required": ["first_action", "supporting_incidents", "insufficient_precedent"],
}

_memory: Optional[HindsightMemory] = None


def get_memory() -> HindsightMemory:
    global _memory
    if _memory is None:
        _memory = HindsightMemory()
    return _memory


def alert_text(alert: AlertIn) -> str:
    return f"{alert.title}\nLog: {alert.log_excerpt}\nContext: {alert.context}".strip()


def analyze(alert: AlertIn, memory: Optional[HindsightMemory] = None) -> AnalyzeResponse:
    started = time.perf_counter()
    warnings: list[str] = []
    if not alert.use_memory:
        return _baseline(alert, started)

    memory = memory or get_memory()
    text = alert_text(alert)

    facts = []
    try:
        facts = memory.recall(text, tags=[config.SERVICE_TAG], max_tokens=3000)
    except HindsightUnavailable as exc:
        log.error("recall failed: %s", exc)
        warnings.append("Memory is unreachable, so no history could be recalled.")

    rec: Optional[Recommendation] = None
    if facts or not warnings:
        try:
            result = memory.reflect(
                PROMPT.format(alert=text),
                response_schema=REFLECT_SCHEMA,
                tags=[config.SERVICE_TAG],
            )
            rec = _to_recommendation(result.structured, result.text)
            if result.structured_error:
                warnings.append("Structured output failed; showing the written answer instead.")
        except HindsightUnavailable as exc:
            log.error("reflect failed: %s", exc)
            warnings.append("Memory reasoning failed; showing recalled history only.")

    grouped = memory_service.group_facts(facts)
    stats = memory_service.runbook_stats()
    mentioned = memory_service.runbooks_mentioned(rec) if rec else []
    return AnalyzeResponse(
        memory_used=True,
        recommendation=rec,
        runbook_stats=[stats[r] for r in mentioned if r in stats],
        evidence=memory_service.build_cards(rec, grouped),
        latency_ms=int((time.perf_counter() - started) * 1000),
        warnings=warnings,
    )


def _clean_ids(values: list[str]) -> list[str]:
    """The model sometimes writes 'INC-002: caused by a leak'. Keep only the bare ID, de-duplicated."""
    seen: list[str] = []
    for value in values:
        for inc in memory_service.INCIDENT_ID.findall(value):
            if inc not in seen:
                seen.append(inc)
    return seen


def _normalise(rec: Recommendation) -> Recommendation:
    rec.supporting_incidents = _clean_ids(rec.supporting_incidents)
    for item in rec.avoid:
        item.incidents = _clean_ids(item.incidents)
    cleaned = []
    for c in rec.contrasting_incidents:
        ids = _clean_ids([c.incident])
        if ids:
            cleaned.append(Contrast(incident=ids[0], difference=c.difference))
    rec.contrasting_incidents = cleaned
    return rec


def _to_recommendation(structured: Optional[dict[str, Any]], text: str) -> Optional[Recommendation]:
    if structured:
        try:
            return _normalise(Recommendation.model_validate(structured))
        except ValidationError as exc:
            log.warning("structured output did not validate: %s", exc)
    if text:  # fall back to the written answer so the engineer still gets something
        return Recommendation(first_action="See reasoning below", reasoning=text[:1500])
    return None


def _baseline(alert: AlertIn, started: float) -> AnalyzeResponse:
    warnings: list[str] = []
    rec: Optional[Recommendation] = None
    try:
        rec = llm.baseline_recommendation(alert)
    except llm.LLMUnavailable as exc:
        log.error("baseline failed: %s", exc)
        warnings.append(f"Baseline unavailable: {exc}")
    return AnalyzeResponse(
        memory_used=False,
        recommendation=rec,
        latency_ms=int((time.perf_counter() - started) * 1000),
        warnings=warnings,
    )
