# Compares memory off vs on across the demo scenarios.
"""Compare the agent with and without memory across the demo alerts, and write eval/results.md.

Usage (backend running on port 8001, venv active, project root):
    python eval/run_eval.py                # one run per variant
    python eval/run_eval.py --runs 3       # repeat, because LLM answers vary between runs
    python eval/run_eval.py --api http://127.0.0.1:8001

What it checks (a HEURISTIC, so always read the raw first actions in results.md yourself):
  * correct   : the first action mentions the fix that actually worked in the recorded incidents
  * bad step  : the first action recommends a step that failed in those incidents
The expected answers come from data/incidents/demo_scenarios.json. They are used only to grade the
output here and are never sent to memory or to the model.
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

# Keywords are matched against the FIRST ACTION text only, lower-cased.
CHECKS = {
    "S1": {"good": ["rb-09", "roll back", "rollback", "previous task definition", "previous version"],
           "bad": ["rb-07", "scale out", "scaling out", "rb-05", "restart"]},
    "S2": {"good": ["rb-11", "health check", "target group"],
           "bad": ["rb-09", "roll back", "rollback", "rb-05", "restart"]},
    "S4": {"good": ["rb-16", "slow quer", "index", "query plan"],
           "bad": ["rb-07", "scale out", "scaling out"]},
}

# (scenario, label, overrides to the alert). "full" is the alert exactly as in the demo file.
VARIANTS = [
    ("S1", "full alert", {}),
    ("S1", "no deploy hint", {"context": ""}),
    ("S2", "full alert", {}),
    ("S2", "less leading", {"context": "No application deploys in the last 9 days."}),
    ("S4", "full alert", {}),
    ("S4", "no context", {"context": ""}),
]


def load_alerts() -> dict[str, dict]:
    path = ROOT / "data" / "incidents" / "demo_scenarios.json"
    return {s["scenario_id"]: s["alert"] for s in json.loads(path.read_text(encoding="utf-8"))["scenarios"] if "alert" in s}


def grade(scenario: str, first_action: str) -> tuple[bool, bool]:
    text = first_action.lower()
    good = any(k in text for k in CHECKS[scenario]["good"])
    bad = any(k in text for k in CHECKS[scenario]["bad"])
    return good and not bad, bad


def call(client: httpx.Client, api: str, alert: dict, use_memory: bool) -> dict:
    body = {"title": alert["title"], "log_excerpt": alert["log_excerpt"], "context": alert["context"], "use_memory": use_memory}
    started = time.perf_counter()
    r = client.post(f"{api}/analyze", json=body)
    r.raise_for_status()
    data = r.json()
    data["_wall_s"] = round(time.perf_counter() - started, 1)
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8001")
    ap.add_argument("--runs", type=int, default=1)
    args = ap.parse_args()

    alerts = load_alerts()
    rows: list[dict] = []
    with httpx.Client(timeout=120) as client:
        try:
            client.get(f"{args.api}/health").raise_for_status()
        except Exception as exc:
            print(f"Cannot reach the API at {args.api}: {exc}")
            return 1
        for scenario, label, override in VARIANTS:
            alert = {**alerts[scenario], **override}
            for run in range(1, args.runs + 1):
                for use_memory in (False, True):
                    mode = "memory" if use_memory else "baseline"
                    try:
                        data = call(client, args.api, alert, use_memory)
                        rec = data.get("recommendation")
                        first = rec["first_action"] if rec else "(no recommendation) " + "; ".join(data.get("warnings", []))
                        ok, bad = grade(scenario, first) if rec else (False, False)
                    except Exception as exc:
                        first, ok, bad, data = f"ERROR: {exc}", False, False, {"_wall_s": 0}
                    rows.append({"scenario": scenario, "label": label, "run": run, "mode": mode,
                                 "first": first, "correct": ok, "bad": bad, "secs": data.get("_wall_s", 0)})
                    print(f"{scenario:<3} {label:<14} run{run} {mode:<8} {'OK ' if ok else 'no '} "
                          f"{'BAD-STEP ' if bad else '         '} {first[:80]}")

    def tally(mode: str) -> str:
        sel = [r for r in rows if r["mode"] == mode]
        return f"{sum(r['correct'] for r in sel)}/{len(sel)} correct, {sum(r['bad'] for r in sel)} recommended a step that failed before"

    print("\nSUMMARY")
    print("  without memory:", tally("baseline"))
    print("  with memory:   ", tally("memory"))

    lines = [
        "# Evaluation: with and without memory", "",
        f"Run on {datetime.now().strftime('%Y-%m-%d %H:%M')}, {args.runs} run(s) per variant, synthetic incident data.", "",
        "**How to read this.** 'Correct' means the first action mentions the fix that worked in the recorded incidents "
        "and no failed step; it is a keyword check, so read the raw first actions below. LLM answers vary between runs, "
        "and this is a small hand-built set, not a benchmark.", "",
        f"- Without memory: {tally('baseline')}", f"- With memory: {tally('memory')}", "",
        "| Alert | Variant | Run | Mode | Correct | Recommends failed step | First action |", "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        first = r["first"].replace("|", "/").replace("\n", " ")
        lines.append(f"| {r['scenario']} | {r['label']} | {r['run']} | {r['mode']} | {'yes' if r['correct'] else 'no'} | "
                     f"{'yes' if r['bad'] else 'no'} | {first} |")
    out = ROOT / "eval" / "results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())