"""The 'teach it something new' test: does the agent learn a lesson that exists in no runbook?

Flow (backend on port 8001, venv active, project root):
    python eval/run_learning_test.py

  1. Analyze alert L1 (a failure type memory has never seen), with and without memory.
  2. POST the engineer's outcome for L1 to /outcomes. It records a fix that is in no runbook.
  3. Keep analyzing a similar alert L2 until memory recommends the new fix, or time runs out.
     This measures how long a newly retained lesson takes to become usable.
  4. Analyze L2 without memory for comparison, then write eval/learning_results.md.

IMPORTANT: this writes a lesson into the memory bank. Run it against a REHEARSAL bank, not the bank
you will demo from, or the demo agent will already 'know' the lesson. Use a rehearsal bank by setting
HINDSIGHT_BANK_ID=incident-response-rehearsal in .env, seeding it, then restarting the backend.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
LESSON_MARKERS = ("fx_live_rates", "cached fx")


def load() -> dict:
    data = json.loads((ROOT / "data" / "incidents" / "demo_scenarios.json").read_text(encoding="utf-8"))
    return {s["scenario_id"]: s for s in data["scenarios"]}


def analyze(client: httpx.Client, api: str, alert: dict, use_memory: bool) -> dict:
    body = {k: alert[k] for k in ("title", "log_excerpt", "context")} | {"use_memory": use_memory}
    r = client.post(f"{api}/analyze", json=body)
    r.raise_for_status()
    return r.json()


def first(data: dict) -> str:
    rec = data.get("recommendation")
    return rec["first_action"] if rec else "(no recommendation) " + "; ".join(data.get("warnings", []))


def learned(data: dict) -> bool:
    rec = data.get("recommendation") or {}
    text = (rec.get("first_action", "") + " " + rec.get("reasoning", "")).lower()
    return any(m in text for m in LESSON_MARKERS) or "INC-011" in rec.get("supporting_incidents", [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8001")
    ap.add_argument("--wait-max", type=int, default=420, help="seconds to keep polling for the lesson")
    ap.add_argument("--interval", type=int, default=20, help="seconds between polls")
    args = ap.parse_args()

    sc = load()
    log: list[str] = []

    def say(msg: str) -> None:
        print(msg)
        log.append(msg)

    with httpx.Client(timeout=120) as client:
        try:
            client.get(f"{args.api}/health").raise_for_status()
        except Exception as exc:
            print(f"Cannot reach the API at {args.api}: {exc}")
            return 1

        say("STEP 1: interaction 1, a failure type memory has not seen")
        b1, m1 = (analyze(client, args.api, sc["L1"]["alert"], False), analyze(client, args.api, sc["L1"]["alert"], True))
        say(f"  without memory: {first(b1)}")
        say(f"  with memory:    {first(m1)}")
        if learned(m1):
            say("  WARNING: memory already knows the lesson. This bank is contaminated; use a fresh rehearsal bank.")
            return 2

        say("\nSTEP 2: the engineer records what actually fixed it (a fix that is in no runbook)")
        out = client.post(f"{args.api}/outcomes", json=sc["L1_OUTCOME"]["outcome"])
        if out.status_code != 200:
            say(f"  FAILED: {out.status_code} {out.text}")
            return 1
        say(f"  retained as {out.json()['incident_id']}")
        t0 = time.time()

        say("\nSTEP 3: interaction 2, a similar alert. Polling until memory uses the lesson")
        found_after = None
        m2 = {}
        while time.time() - t0 <= args.wait_max:
            m2 = analyze(client, args.api, sc["L2"]["alert"], True)
            elapsed = int(time.time() - t0)
            ok = learned(m2)
            say(f"  +{elapsed:>3}s  learned={'YES' if ok else 'no '}  {first(m2)[:100]}")
            if ok:
                found_after = elapsed
                break
            time.sleep(args.interval)

        say("\nSTEP 4: the same similar alert without memory")
        b2 = analyze(client, args.api, sc["L2"]["alert"], False)
        say(f"  without memory: {first(b2)}")

    say("\nRESULT")
    if found_after is None:
        say(f"  Memory did NOT use the new lesson within {args.wait_max}s. Read the polling lines above.")
    else:
        say(f"  Memory used the new lesson about {found_after}s after it was recorded.")
        say(f"  With memory: {first(m2)}")
        say(f"  Without memory: {first(b2)}")

    lines = ["# Learning test: a lesson that exists in no runbook", "",
             f"Run on {datetime.now().strftime('%Y-%m-%d %H:%M')} against a synthetic bank.", "", "```"] + log + ["```", ""]
    (ROOT / "eval" / "learning_results.md").write_text("\n".join(lines), encoding="utf-8")
    print("\nWrote eval/learning_results.md")
    return 0 if found_after is not None else 3


if __name__ == "__main__":
    sys.exit(main())
