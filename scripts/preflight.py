"""Pre-recording checks. Run from the project root with the venv active (backend may be running).

    python scripts/preflight.py

It never prints your keys. It checks that the bank is seeded, that the bank does NOT already
contain the FX lesson used in the demo, that runtime data is clean, and that the running backend
uses the same bank as your .env.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402
from app.services.hindsight_client import HindsightMemory, HindsightUnavailable  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    return ok


def run(memory: HindsightMemory, backend_url: str = "http://127.0.0.1:8001") -> bool:
    results = [
        check("HINDSIGHT_API_KEY is set", bool(config.HINDSIGHT_API_KEY)),
        check("LLM_API_KEY is set (needed for the no-memory column)", bool(config.LLM_API_KEY)),
        check("no leftover runtime data", not (config.RUNTIME_DIR / "incidents.json").exists(),
              "delete the data/runtime folder before recording"),
    ]
    print(f"      bank in .env: {config.BANK_ID}")
    try:
        facts = memory.recall("connection pool exhausted latency 502 after deploy",
                              tags=[config.SERVICE_TAG], max_tokens=1500)
        results.append(check("bank is seeded (incident facts come back)", any("INC-" in f.text for f in facts),
                             f"{len(facts)} facts; run scripts/seed_memory.py if this fails"))
        lesson = memory.recall("fx_live_rates feature flag cached FX rates rates-service timeout",
                               tags=[config.SERVICE_TAG], max_tokens=1500)
        results.append(check("bank does NOT already know the FX lesson",
                             not any("fx_live_rates" in f.text.lower() for f in lesson),
                             "if this fails, use a new HINDSIGHT_BANK_ID and seed it"))
    except HindsightUnavailable as exc:
        results.append(check("Hindsight is reachable", False, str(exc)[:120]))

    try:
        health = httpx.get(f"{backend_url}/health", timeout=5).json()
        results.append(check("backend is running", True))
        results.append(check("backend uses the same bank as .env", health.get("bank") == config.BANK_ID,
                             f"backend says '{health.get('bank')}'; restart uvicorn after editing .env"))
    except Exception:
        results.append(check("backend is running on port 8001", False, "start uvicorn"))
    return all(results)


def main() -> int:
    memory = HindsightMemory()
    try:
        ok = run(memory)
    finally:
        memory.close()
    print("\nAll checks passed." if ok else "\nFix the FAIL lines above, then run this again.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())