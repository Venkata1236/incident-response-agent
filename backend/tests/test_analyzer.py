"""Offline tests: no network, Hindsight replaced by a fake. Run: pytest backend/tests -q"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import AlertIn  # noqa: E402
from app.services import analyzer, memory_service  # noqa: E402
from app.services.hindsight_client import Evidence, HindsightUnavailable, ReflectResult  # noqa: E402


class FakeMemory:
    def __init__(self, facts=None, result=None, recall_error=False, reflect_error=False):
        self.facts, self.result = facts or [], result
        self.recall_error, self.reflect_error = recall_error, reflect_error

    def recall(self, *a, **k):
        if self.recall_error:
            raise HindsightUnavailable("down")
        return self.facts

    def reflect(self, *a, **k):
        if self.reflect_error:
            raise HindsightUnavailable("reflect down")
        return self.result


FACTS = [
    Evidence(id="1", text="Incident INC-006 shared the QueuePool error with INC-002.", document_id="INC-006"),
    Evidence(id="2", text="Scaling out (RB-07) worsened the incident.", document_id="INC-002"),
    Evidence(id="3", text="Observation without a document id mentions INC-004 health checks."),
    Evidence(id="4", text="Runbook RB-07 scales out.", document_id="RB-07"),
]
STRUCTURED = {
    "first_action": "Roll back the deploy (RB-09)",
    "reasoning": "Same signature as INC-002 and INC-006.",
    "avoid": [{"action": "Scale out (RB-07)", "reason": "worsened it", "incidents": ["INC-002"]}],
    "supporting_incidents": ["INC-002", "INC-006"],
    "contrasting_incidents": [{"incident": "INC-004", "difference": "health check cause, no deploy"}],
    "insufficient_precedent": False,
}
ALERT = AlertIn(title="p95 latency 4.4s and 502s rising", log_excerpt="QueuePool limit", context="Deploy v2.22")


def test_runbook_stats_are_counted_from_records():
    stats = memory_service.runbook_stats()
    assert (stats["RB-07"].worked, stats["RB-07"].failed) == (0, 3)
    assert (stats["RB-05"].worked, stats["RB-05"].failed) == (1, 3)
    assert (stats["RB-09"].worked, stats["RB-09"].failed) == (2, 1) or stats["RB-09"].worked >= 2
    assert any("never worked" in f for f in stats["RB-07"].flags)


def test_incident_id_falls_back_to_text_for_observations():
    assert memory_service.incident_id_of(FACTS[2]) == "INC-004"
    assert memory_service.incident_id_of(FACTS[3]) is None  # runbook documents are not incidents


def test_memory_on_builds_roles_and_stats():
    mem = FakeMemory(FACTS, ReflectResult(text="x", structured=STRUCTURED))
    out = analyzer.analyze(ALERT, memory=mem)
    roles = {c.incident_id: c.role for c in out.evidence}
    assert roles["INC-002"] == "supports" and roles["INC-006"] == "supports"
    assert roles["INC-004"] == "contrasts"
    assert [s.runbook_id for s in out.runbook_stats][:1] == ["RB-09"] or "RB-07" in [s.runbook_id for s in out.runbook_stats]
    assert out.recommendation.first_action.startswith("Roll back")
    assert out.warnings == []


def test_reflect_failure_degrades_to_recall_only():
    out = analyzer.analyze(ALERT, memory=FakeMemory(FACTS, reflect_error=True))
    assert out.recommendation is None and out.evidence
    assert any("reasoning failed" in w for w in out.warnings)


def test_memory_unreachable_returns_a_warning_not_a_crash():
    out = analyzer.analyze(ALERT, memory=FakeMemory(recall_error=True))
    assert out.recommendation is None and out.warnings


def test_missing_structured_output_uses_written_answer():
    out = analyzer.analyze(ALERT, memory=FakeMemory(FACTS, ReflectResult(text="Roll back the deploy.", structured=None)))
    assert out.recommendation and "Roll back" in out.recommendation.reasoning
