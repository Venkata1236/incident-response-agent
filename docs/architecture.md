# Architecture

## Overview

```text
                    +-------------------------------------------+
  React UI  ------> |  FastAPI (port 8001)                       |
  (Vite, TS)        |   POST /analyze   analyzer.py              |
                    |   POST /outcomes  outcome_service.py       |
                    |   GET  /incidents memory_service.py        |
                    +-----------------+-------------------------+
                                      |
              +-----------------------+------------------------+
              |                                                |
   memory ON  v                                     memory OFF  v
   hindsight_client.py                              llm.py (baseline)
   recall -> reflect                                alert + runbooks only
              |
              v
   Hindsight (one bank, tagged memories)
              |
   deterministic layer: runbook stats, evidence cards (memory_service.py)
```

## Components

| Component | Responsibility |
|---|---|
| `hindsight_client.py` | The only module that calls Hindsight: retain, recall, reflect, bank creation, retries |
| `analyzer.py` | Runs recall, then reflect, then adds deterministic stats; falls back gracefully |
| `memory_service.py` | Incident catalog, runbook statistics, grouping recalled facts into evidence cards |
| `outcome_service.py` | Turns an engineer's report into a memory, by template, and retains it |
| `llm.py` | The no-memory baseline through any OpenAI-compatible API |
| `schemas.py` | Request and response models |
| `frontend/` | One screen: alert, mode toggle, recommendation, evidence, outcome form |

## Request flow: analyze with memory

1. The UI posts the alert to `/analyze`.
2. Recall (no LLM) fetches relevant facts, scoped to the service tag.
3. Reflect reasons over memory and returns a structured recommendation.
4. The analyzer normalises incident IDs, then adds runbook statistics counted from recorded outcomes.
5. Facts are grouped by incident and turned into evidence cards labelled *matches*, *looks similar but differs*
   or *also recalled*.
6. The response includes latency and any warnings.

Handlers are plain `def`, not `async def`. The Hindsight client runs its own event loop, and FastAPI runs sync
handlers in a worker thread, which avoids a nested-loop clash.

## Request flow: record an outcome (the live write)

1. The engineer lists the steps taken, marks each *worked* or *did not work*, and states the root cause.
2. `outcome_service` builds the memory text by template and retains it with the incident ID as `document_id`,
   tags and a timestamp.
3. Only after retain succeeds is a local copy written to `data/runtime/` so runbook statistics update.
4. Re-using an incident ID overwrites the earlier record instead of duplicating it.

## Failure handling

| Failure | Behaviour |
|---|---|
| Hindsight unreachable | Warning in the response, no crash |
| Reflect fails | Recalled history is still returned, with a warning |
| Structured output missing | The written answer is shown instead |
| Baseline model fails | Retries three times, then a visible warning |
| Retain fails | HTTP 502, nothing saved locally |
| Malformed IDs from the model | Normalised to `INC-###` |

## Security and safety notes

- Alert text is untrusted. It is delimited in the prompt and the model is told to treat it as data.
- Secrets live only in `.env`, which is git-ignored.
- CORS accepts only local origins.
- The app is decision support. It never executes a remediation step.

## Testing

`backend/tests` holds offline tests that replace Hindsight with a fake: runbook counts, incident-ID handling,
graceful degradation, outcome retention and validation. `eval/run_eval.py` and `eval/run_learning_test.py` run
against the live stack.

## Not built (deliberately)

Authentication, multi-tenant banks, a database, a supersession model for decisions that overturn earlier ones,
and integrations with paging or ticketing systems.
