# Incident Response Agent

**Incident response that remembers what worked.**

An on-call assistant for the `payments-api` service, built on [Hindsight](https://github.com/vectorize-io/hindsight)
agent memory. It remembers past incidents, which fixes worked, which failed, and how each new alert differs from
what it has seen before. A human always makes the final call.

> All incident data in this repository is **synthetic**: a fictional service and fictional incidents, modeled on
> failure patterns that appear in public postmortems. It is not real company data.

## The problem

At 3 a.m. the on-call engineer sees an alert. The history that would help lives in old tickets, chat threads and the
heads of engineers who are asleep. So teams repeat fixes that already failed: restarting a service that has a
connection leak, or scaling out a service whose real bottleneck is the database.

Runbooks describe what to do in general. They do not record what happened the last time, and they cannot say
"this runbook has failed on the last three incidents".

## What it does

| Without memory | With memory |
|---|---|
| Sees the alert and the runbooks | Also recalls past incidents through Hindsight |
| Picks the runbook that matches the symptom | Says which earlier fixes failed here, and cites the incidents |
| Cannot know a lesson that is in no runbook | Uses lessons the team recorded after earlier incidents |

The screen has three modes: **With memory**, **Without memory**, and **Compare** (both side by side). After an
analysis, the engineer can record what worked and what did not. That outcome is stored in memory immediately.

## Results so far (small, synthetic, single runs)

These are honest, early numbers from a small hand-built set. They are not a benchmark.

- **With and without memory, six alert variants** (`eval/run_eval.py`, one run each, keyword-graded): without memory
  5 of 6 first actions were correct, with memory 6 of 6. **The runbooks alone are enough for most of these alerts**,
  so memory's edge on the first action is small. Raw answers are in `eval/results.md`.
- **Learning a lesson that exists in no runbook** (`eval/run_learning_test.py`, one run): the agent first gave a
  generic answer, the engineer recorded that disabling a feature flag fixed the incident, and about 8 seconds later
  a similar alert produced that recommendation. The no-memory baseline recommended scaling out both times. Details
  in `eval/learning_results.md`.

## How Hindsight is used

Retain, recall and reflect each do a distinct job. See [docs/hindsight-usage.md](docs/hindsight-usage.md).

- **Retain** stores each incident and runbook with its original timestamp, tags and a stable `document_id`. Outcomes
  are written as explicit "worked" or "did not work" sentences, so they are never left for extraction to infer.
- **Recall** (no LLM call) retrieves relevant facts for the evidence panel.
- **Reflect** reasons over memory and returns a structured recommendation: first action, what to avoid and why,
  matching incidents, and incidents that look similar but differ.
- **Counts are computed in code**, not by the model. For example, "RB-07 worked 0 of 3 times" comes from the
  recorded outcomes.

## Architecture

```text
React UI  --->  FastAPI  --->  analyzer  --->  Hindsight (one bank, tagged memories)
 (Vite)        /analyze          recall -> reflect -> deterministic runbook stats
               /outcomes         retain a new outcome
               /incidents        past incidents
                                  |
                                  +--> baseline LLM (no memory), for the comparison
```

More detail in [docs/architecture.md](docs/architecture.md).

## Run it

Requirements: Python 3.10+, Node 18+, a Hindsight Cloud account and API key, and an API key for an
OpenAI-compatible LLM (Groq works) for the no-memory baseline.

```bash
# 1. Backend
python -m venv .venv
.venv\Scripts\activate            # Windows. On macOS or Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env              # then fill in the keys
python scripts/seed_memory.py     # loads 8 runbooks and 10 incidents; wait about a minute afterwards
uvicorn app.main:app --app-dir backend --port 8001

# 2. Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Open the address Vite prints (usually http://localhost:5173). The API listens on port 8001.

`.env` settings: `HINDSIGHT_URL`, `HINDSIGHT_API_KEY`, `HINDSIGHT_BANK_ID`, `LLM_API_KEY`, `LLM_MODEL`,
`LLM_BASE_URL`. See `.env.example`.

### Tests and evaluation

```bash
pytest backend/tests -q           # offline tests, no network needed
python eval/run_eval.py           # with vs without memory across the demo alerts
python eval/run_learning_test.py  # teach it a lesson, then check it is used (use a spare bank)
```

## Limitations

- The data is synthetic and small. The results above are single runs, so treat them as signals.
- Recommendations are LLM reasoning over retained history, not a trained model. Answers can vary between runs.
- On alerts that map directly to a runbook, a good LLM with the runbooks does about as well without memory.
  Memory's value is in lessons that are in no runbook, cited evidence, and counted track records.
- A reflect call takes around ten seconds in our runs.
- Tags are a soft partition inside one bank. A real multi-team deployment would use a bank per tenant.
- There is no handling yet for a newer decision that supersedes an older one.
- Decision support only: a human decides.

## Credits

Built with [Hindsight](https://github.com/vectorize-io/hindsight) by Vectorize.
