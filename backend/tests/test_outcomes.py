"""Offline tests for the live outcome write. Run: pytest backend/tests -q"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.main import app  # noqa: E402
from app.services import analyzer, memory_service  # noqa: E402
from app.services.hindsight_client import HindsightUnavailable  # noqa: E402

BODY = {
    "title": "p95 latency 4.4s and 502s rising after v2.22",
    "log_excerpt": "QueuePool limit of size 20 overflow 10 reached",
    "context": "Deploy v2.22 shipped 40 minutes ago.",
    "steps": [
        {"step": "Roll back to the previous version", "runbook": "RB-09", "worked": True},
        {"step": "Scale out the service", "runbook": "RB-07", "worked": False},
    ],
    "root_cause": "another connection leak introduced by v2.22",
    "cause_tag": "connection_leak",
    "minutes_to_resolve": 9,
    "resolved_by": "Venkat",
}


class RecordingMemory:
    def __init__(self, fail=False):
        self.items, self.fail = [], fail

    def retain_items(self, items, attempts=4):
        if self.fail:
            raise HindsightUnavailable("down")
        self.items += items


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNTIME_DIR", tmp_path)
    return TestClient(app)


def test_outcome_is_retained_with_explicit_worked_and_failed_sentences(client):
    mem = RecordingMemory()
    analyzer._memory = mem
    r = client.post("/outcomes", json=BODY)
    assert r.status_code == 200 and r.json()["incident_id"] == "INC-011"
    item = mem.items[0]
    assert "Roll back to the previous version (RB-09) worked." in item["content"]
    assert "Scale out the service (RB-07) did not work." in item["content"]
    assert item["document_id"] == "INC-011" and "cause:connection_leak" in item["tags"]
    assert "runbook:RB-09" in item["tags"] and "runbook:RB-07" in item["tags"]


def test_local_record_updates_runbook_stats(client, tmp_path):
    analyzer._memory = RecordingMemory()
    before = memory_service.runbook_stats()["RB-07"].failed
    client.post("/outcomes", json=BODY)
    after = memory_service.runbook_stats()["RB-07"].failed
    assert after == before + 1
    assert json.loads((tmp_path / "incidents.json").read_text())[0]["incident_id"] == "INC-011"


def test_reusing_an_id_overwrites_instead_of_duplicating(client, tmp_path):
    analyzer._memory = RecordingMemory()
    client.post("/outcomes", json={**BODY, "incident_id": "INC-011"})
    client.post("/outcomes", json={**BODY, "incident_id": "INC-011", "minutes_to_resolve": 12})
    rows = json.loads((tmp_path / "incidents.json").read_text())
    assert len(rows) == 1 and rows[0]["minutes_to_resolve"] == 12


def test_failed_retain_saves_nothing_locally(client, tmp_path):
    analyzer._memory = RecordingMemory(fail=True)
    r = client.post("/outcomes", json=BODY)
    assert r.status_code == 502
    assert not (tmp_path / "incidents.json").exists()


def test_validation_rejects_bad_runbook_id(client):
    bad = {**BODY, "steps": [{"step": "Restart tasks", "runbook": "restart", "worked": False}]}
    assert client.post("/outcomes", json=bad).status_code == 422
