"""Turns an engineer's outcome report into a memory: the live write of the demo.

The memory text is built by plain string templating, NOT by an LLM, so what is retained is exactly
what the engineer reported. Each step gets an explicit "worked" or "did not work" sentence, because
outcomes are the whole point of this memory and must never be left for extraction to infer.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app import config
from app.schemas import OutcomeIn, OutcomeOut
from app.services import memory_service
from app.services.hindsight_client import HindsightMemory

log = logging.getLogger(__name__)


def next_incident_id(existing: dict[str, Any]) -> str:
    numbers = [int(m.group(1)) for k in existing if (m := re.fullmatch(r"INC-(\d{3})", k))]
    return f"INC-{(max(numbers) + 1 if numbers else 1):03d}"


def _step_sentence(step) -> str:
    label = f"{step.step} ({step.runbook})" if step.runbook else step.step
    return f"{label} {'worked' if step.worked else 'did not work'}."


def build_memory_text(o: OutcomeIn, incident_id: str, when: datetime) -> str:
    worked = [s for s in o.steps if s.worked]
    failed = [s for s in o.steps if not s.worked]
    parts = [
        f"Incident {incident_id} ({o.severity}): On {when.day} {when.strftime('%B %Y')} payments-api had a "
        f"{o.severity} incident: {o.title}.",
    ]
    if o.log_excerpt:
        parts.append(f"Logs showed {o.log_excerpt.rstrip('. ')}.")
    if o.context:
        parts.append(o.context if o.context.rstrip().endswith(".") else o.context.rstrip() + ".")
    parts += [_step_sentence(s) for s in o.steps]
    parts.append(f"The root cause was {o.root_cause.rstrip('.')}.")
    if o.minutes_to_resolve is not None:
        parts.append(f"It took {o.minutes_to_resolve} minutes, resolved by {o.resolved_by}.")
    outcome = "Outcome: " + ("; ".join(s.step for s in worked) or "nothing") + " worked"
    if failed:
        outcome += "; " + "; ".join(s.step for s in failed) + " did not work"
    parts.append(outcome + ".")
    return " ".join(parts)


def _record(o: OutcomeIn, incident_id: str, when: datetime, memory_text: str, tags: list[str]) -> dict[str, Any]:
    worked = [s.step for s in o.steps if s.worked]
    failed = [s.step for s in o.steps if not s.worked]
    return {
        "incident_id": incident_id,
        "timestamp": when.isoformat(),
        "service": "payments-api",
        "severity": o.severity,
        "symptom": o.title,
        "log_excerpt": o.log_excerpt,
        "steps_tried": [
            {"step": s.step, "runbook": s.runbook or "", "result": "worked" if s.worked else "did not work"}
            for s in o.steps
        ],
        "root_cause": o.root_cause,
        "resolution": "; ".join(worked),
        "what_worked": "; ".join(worked),
        "what_failed": "; ".join(failed),
        "minutes_to_resolve": o.minutes_to_resolve,
        "resolved_by": o.resolved_by,
        "tags": tags,
        "memory_text": memory_text,
    }


def _save_runtime(record: dict[str, Any]) -> None:
    config.RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    path = config.RUNTIME_DIR / "incidents.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    rows = [r for r in rows if r["incident_id"] != record["incident_id"]]  # overwrite = repeatable demo
    rows.append(record)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def record_outcome(o: OutcomeIn, memory: HindsightMemory) -> OutcomeOut:
    """Retain first. Only if that succeeds is the local record written, so the two never disagree."""
    when = datetime.now(timezone.utc).astimezone()
    incident_id = o.incident_id or next_incident_id(memory_service.load_incidents())
    memory_text = build_memory_text(o, incident_id, when)

    tags = [config.SERVICE_TAG, "type:incident", f"incident:{incident_id}", "outcome:resolved"]
    tags += [f"runbook:{s.runbook}" for s in o.steps if s.runbook]
    if o.cause_tag:
        tags.append(f"cause:{o.cause_tag}")
    tags = list(dict.fromkeys(tags))  # de-duplicate, keep order

    item: dict[str, Any] = {
        "content": memory_text,
        "context": "payments-api incident postmortem",
        "timestamp": when.isoformat(),
        "document_id": incident_id,
        "tags": tags,
        "metadata": {
            "incident_id": incident_id,
            "severity": o.severity,
            "minutes_to_resolve": str(o.minutes_to_resolve if o.minutes_to_resolve is not None else ""),
            "resolved_by": o.resolved_by,
            "source": "live-outcome",
        },
    }
    if config.OBSERVATION_SCOPES:
        item["observation_scopes"] = config.OBSERVATION_SCOPES

    memory.retain_items([item])  # raises HindsightUnavailable on failure; nothing is saved locally then
    _save_runtime(_record(o, incident_id, when, memory_text, tags))
    log.info("Retained live outcome %s", incident_id)
    return OutcomeOut(incident_id=incident_id, retained=True, memory_text=memory_text)
