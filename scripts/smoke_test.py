"""Quick check that memory answers the way the demo needs it to.

Usage (project root, venv active, a minute after seeding):
    python scripts/smoke_test.py            # recall only: fast, no LLM cost
    python scripts/smoke_test.py --reflect  # also run reflect (slower, uses LLM tokens)
    python scripts/smoke_test.py --scenario S2

It reads only the ALERT part of a demo scenario. The 'expected' answers are never sent anywhere.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402
from app.services.hindsight_client import HindsightMemory, HindsightUnavailable  # noqa: E402

REFLECT_SCHEMA = {
    "type": "object",
    "properties": {
        "first_action": {"type": "string"},
        "avoid": {"type": "array", "items": {"type": "string"}},
        "cited_incidents": {"type": "array", "items": {"type": "string"}},
        "difference_from_past": {"type": "string"},
    },
    "required": ["first_action", "avoid", "cited_incidents"],
}


def alert_query(scenario_id: str) -> str:
    with open(config.DATA_DIR / "demo_scenarios.json", encoding="utf-8") as fh:
        scenarios = {s["scenario_id"]: s for s in json.load(fh)["scenarios"]}
    alert = scenarios[scenario_id]["alert"]
    return f"{alert['title']}. Log: {alert['log_excerpt']} Context: {alert['context']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default="S1", help="S1, S2, S3 or S4 (default S1)")
    parser.add_argument("--reflect", action="store_true", help="also run reflect")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    memory = HindsightMemory()
    query = alert_query(args.scenario)
    print(f"SCENARIO {args.scenario}\nQUERY: {query}\n")

    try:
        print("=== RECALL (no LLM) ===")
        facts = memory.recall(query, tags=[config.SERVICE_TAG], max_tokens=3000)
        print(f"{len(facts)} facts returned\n")
        by_doc: "OrderedDict[str, list]" = OrderedDict()
        for f in facts:
            by_doc.setdefault(f.document_id or "(no document)", []).append(f)
        for doc, items in by_doc.items():
            print(f"[{doc}]")
            for f in items[:2]:
                print(f"   - ({f.type}) {f.text[:150]}")

        if args.reflect:
            print("\n=== REFLECT (LLM, cited sources) ===")
            result = memory.reflect(
                "What should the on-call engineer do first for this alert, which earlier fixes "
                "failed on this kind of problem, and how does this alert differ from past incidents? "
                "Cite incident IDs. Alert: " + query,
                response_schema=REFLECT_SCHEMA,
                tags=[config.SERVICE_TAG],
            )
            print(result.text[:1500])
            print("\nSTRUCTURED:", json.dumps(result.structured, indent=2) if result.structured else None)
            if result.structured_error:
                print("STRUCTURED ERROR:", result.structured_error)
            print(f"\nSOURCES CITED: {len(result.sources)}")
            for s in result.sources[:8]:
                print(f"   - ({s.type}) {s.text[:120]}")
    except HindsightUnavailable as exc:
        print("FAILED:", exc)
        return 1
    finally:
        memory.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())