"""Central configuration. Everything comes from environment variables (.env at the project root)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

# --- Hindsight ---------------------------------------------------------------
# Hindsight Cloud URL is shown in the docs as https://api.hindsight.vectorize.io.
# Confirm it in your dashboard. For a local server use http://localhost:8888.
HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incident-response-agent")

# --- LLM (used only by the analyzer, later) ----------------------------------
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
# Groq exposes an OpenAI-compatible API. Change this if you use another provider.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")

# --- Memory design -----------------------------------------------------------
# One bank, many tags. A bank is the unit of isolation in Hindsight and there is no
# cross-bank query, so a single bank keeps org-level questions possible.
SERVICE_TAG = "service:payments-api"

# How Hindsight consolidates retained facts into observations. "per_tag" builds one
# observation per tag, so a tag such as cause:connection_leak accumulates evidence
# across incidents instead of staying locked inside a single incident.
OBSERVATION_SCOPES = os.getenv("OBSERVATION_SCOPES", "per_tag")

DATA_DIR = ROOT_DIR / "data" / "incidents"
RUNTIME_DIR = ROOT_DIR / "data" / "runtime"  # outcomes logged live during the demo (git-ignored)
