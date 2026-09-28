# Loads incidents.json and runbooks.json into Hindsight (retain, one call per item).
"""Load the synthetic incidents and runbooks into Hindsight.

Usage (from the project root, venv active):
    python scripts/seed_memory.py --dry-run        # print what would be retained, no network
    python scripts/seed_memory.py --check          # confirm URL, key and bank respond (recall only)
    python scripts/seed_memory.py                  # seed everything
    python scripts/seed_memory.py --only INC-002   # seed one item

Notes
* Idempotent: every item has a stable document_id, so re-running replaces instead of duplicating.
* Only incidents.json and runbooks.json are retained. demo_scenarios.json (which holds the
  expected answers) is never sent to memory.
* Hindsight consolidates facts into observations in the background. After seeding, wait about
  a minute before testing recall or reflect.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  
from app.services.hindsight_client import HindsightMemory, HindsightUnavailable 

log = logging.getLogger("seed")


def load_json(name: str) -> dict[str, Any]:
    with open(config.DATA_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


def incident_item(inc: dict[str, Any], scopes: str | None) -> dict[str, Any]:
    """One incident becomes one document. The ID is written into the text so cited facts stay traceable."""
    item: dict[str, Any] = {
        "content": f"Incident {inc['incident_id']} ({inc['severity']}): {inc['memory_text']}",
        "context": "payments-api incident postmortem",
        "timestamp": inc["timestamp"],
        "document_id": inc["incident_id"],
        "tags": list(inc["tags"]) + [f"incident:{inc['incident_id']}", "type:incident"],
        "metadata": {
            "incident_id": inc["incident_id"],
            "severity": inc["severity"],
            "minutes_to_resolve": str(inc["minutes_to_resolve"]),
            "resolved_by": inc["resolved_by"],
        },
    }
    if scopes:
        item["observation_scopes"] = scopes
    return item


def runbook_item(rb: dict[str, Any], scopes: str | None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "content": (
            f"Runbook {rb['runbook_id']}: {rb['title']}. Steps: {rb['steps']} "
            f"This runbook was last reviewed on {rb['last_reviewed']}."
        ),
        "context": "payments-api runbook",
        "timestamp": f"{rb['last_reviewed']}T00:00:00Z",
        "document_id": rb["runbook_id"],
        "tags": [config.SERVICE_TAG, "type:runbook", f"runbook:{rb['runbook_id']}"],
        "metadata": {"runbook_id": rb["runbook_id"], "last_reviewed": rb["last_reviewed"]},
    }
    if scopes:
        item["observation_scopes"] = scopes
    return item


def build_items(scopes: str | None, only: str | None) -> list[dict[str, Any]]:
    items = [runbook_item(r, scopes) for r in load_json("runbooks.json")["runbooks"]]
    items += [incident_item(i, scopes) for i in load_json("incidents.json")["incidents"]]
    items.sort(key=lambda it: it["timestamp"])  # oldest first
    if only:
        items = [it for it in items if it["document_id"] == only]
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print items, do not call Hindsight")
    parser.add_argument("--check", action="store_true", help="test connectivity with one recall")
    parser.add_argument("--only", help="seed a single document_id, e.g. INC-002")
    parser.add_argument("--no-scopes", action="store_true", help="do not send observation_scopes")
    parser.add_argument("--delay", type=float, default=2.0, help="seconds between calls (avoid 429s)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    memory = HindsightMemory()

    if args.check:
        try:
            found = memory.recall("payments-api incident", tags=[config.SERVICE_TAG])
        except HindsightUnavailable as exc:
            log.error("Hindsight check failed: %s", exc)
            return 1
        log.info("Connected to bank '%s'. Recall returned %d facts.", memory.bank_id, len(found))
        return 0

    scopes = None if args.no_scopes else config.OBSERVATION_SCOPES
    items = build_items(scopes, args.only)
    if not items:
        log.error("No items matched.")
        return 1

    if args.dry_run:
        for it in items:
            print(f"--- {it['document_id']}  {it['timestamp']}  tags={it['tags']}")
            print(it["content"][:160] + ("..." if len(it["content"]) > 160 else ""))
        print(f"\n{len(items)} items would be retained into bank '{memory.bank_id}'.")
        return 0

    log.info("Seeding %d items into bank '%s' ...", len(items), memory.bank_id)
    for n, it in enumerate(items, start=1):
        try:
            memory.retain_items([it])
        except HindsightUnavailable as exc:
            log.error("Stopped at %s: %s", it["document_id"], exc)
            return 1
        log.info("[%d/%d] retained %s", n, len(items), it["document_id"])
        time.sleep(args.delay)

    log.info("Done. Wait about a minute for background consolidation before recall or reflect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())