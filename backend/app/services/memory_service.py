"""Deterministic helpers around the memory: incident catalog, runbook statistics, evidence cards.

Design rule: anything that is a COUNT or a DATE is computed here in code from recorded records.
The LLM explains and recommends; it never produces the numbers the UI shows.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any, Optional

from app import config
from app.schemas import EvidenceCard, Recommendation, RunbookStat
from app.services.hindsight_client import Evidence

INCIDENT_ID = re.compile(r"\bINC-\d{3}\b")
RUNBOOK_ID = re.compile(r"\bRB-\d{2}\b")


# --------------------------------------------------------------------- catalog
def _read_json(path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_incidents() -> dict[str, dict[str, Any]]:
    """Seed incidents plus any outcomes logged live (data/runtime/incidents.json), keyed by ID."""
    catalog = {i["incident_id"]: i for i in _read_json(config.DATA_DIR / "incidents.json")["incidents"]}
    live = config.RUNTIME_DIR / "incidents.json"
    if live.exists():
        for inc in _read_json(live):
            catalog[inc["incident_id"]] = inc
    return catalog


def load_runbooks() -> dict[str, dict[str, Any]]:
    return {r["runbook_id"]: r for r in _read_json(config.DATA_DIR / "runbooks.json")["runbooks"]}


# ------------------------------------------------------------ runbook statistics
def _step_worked(result: str) -> bool:
    """A step counts as a success only when its recorded result starts with 'worked'."""
    return result.strip().lower().startswith("worked")


def runbook_stats(as_of: Optional[date] = None) -> dict[str, RunbookStat]:
    as_of = as_of or date.today()
    runbooks = load_runbooks()
    counts: dict[str, list[int]] = {rid: [0, 0] for rid in runbooks}  # [worked, failed]
    for inc in load_incidents().values():
        for step in inc.get("steps_tried", []):
            rid = step.get("runbook") or ""
            if rid in counts:
                counts[rid][0 if _step_worked(step.get("result", "")) else 1] += 1

    stats: dict[str, RunbookStat] = {}
    for rid, rb in runbooks.items():
        worked, failed = counts[rid]
        uses = worked + failed
        reviewed = rb.get("last_reviewed")
        days = (as_of - datetime.strptime(reviewed, "%Y-%m-%d").date()).days if reviewed else None
        flags: list[str] = []
        if uses >= 3 and worked == 0:
            flags.append("never worked: review or retire")
        elif uses >= 3 and worked / uses <= 0.25:
            flags.append("low success rate")
        if days is not None and days > 180:
            flags.append("not reviewed in over 6 months")
        stats[rid] = RunbookStat(
            runbook_id=rid, title=rb["title"], uses=uses, worked=worked, failed=failed,
            last_reviewed=reviewed, days_since_review=days, flags=flags,
        )
    return stats


def runbooks_mentioned(rec: Recommendation) -> list[str]:
    text = " ".join([rec.first_action, rec.reasoning] + [f"{a.action} {a.reason}" for a in rec.avoid])
    seen: list[str] = []
    for rid in RUNBOOK_ID.findall(text):
        if rid not in seen:
            seen.append(rid)
    return seen


# ---------------------------------------------------------------------- evidence
def incident_id_of(fact: Evidence) -> Optional[str]:
    """Facts carry a document_id when raw; consolidated observations do not, so fall back to the text."""
    if fact.document_id and INCIDENT_ID.fullmatch(fact.document_id):
        return fact.document_id
    match = INCIDENT_ID.search(fact.text)
    return match.group(0) if match else None


def group_facts(facts: list[Evidence], per_incident: int = 2) -> dict[str, list[str]]:
    """Group recalled facts by incident, keeping recall (relevance) order."""
    grouped: dict[str, list[str]] = {}
    for fact in facts:
        inc = incident_id_of(fact)
        if not inc:
            continue
        bucket = grouped.setdefault(inc, [])
        if len(bucket) < per_incident and fact.text not in bucket:
            bucket.append(fact.text)
    return grouped


def build_cards(rec: Optional[Recommendation], grouped: dict[str, list[str]], limit: int = 6) -> list[EvidenceCard]:
    catalog = load_incidents()
    roles: dict[str, str] = {}
    if rec:
        for inc in rec.supporting_incidents:
            roles.setdefault(inc, "supports")
        for c in rec.contrasting_incidents:
            roles.setdefault(c.incident, "contrasts")
    for inc in grouped:  # related = recalled but not named by the recommendation, in relevance order
        roles.setdefault(inc, "related")

    order = {"supports": 0, "contrasts": 1, "related": 2}
    ids = sorted(roles, key=lambda i: (order[roles[i]], list(grouped).index(i) if i in grouped else 99))
    # Recall is broad and can pull in loosely related incidents, so show at most two of those.
    named = [i for i in ids if roles[i] != "related"]
    related = [i for i in ids if roles[i] == "related"][:2]
    cards: list[EvidenceCard] = []
    for inc_id in (named + related)[:limit]:
        rec_data = catalog.get(inc_id, {})
        cards.append(
            EvidenceCard(
                incident_id=inc_id,
                role=roles[inc_id],  # type: ignore[arg-type]
                date=(rec_data.get("timestamp") or "")[:10] or None,
                summary=rec_data.get("symptom"),
                root_cause=rec_data.get("root_cause"),
                what_worked=rec_data.get("what_worked") or None,
                what_failed=rec_data.get("what_failed") or None,
                minutes_to_resolve=rec_data.get("minutes_to_resolve"),
                remembered_facts=grouped.get(inc_id, []),
            )
        )
    return cards
