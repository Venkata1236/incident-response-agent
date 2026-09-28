# How Hindsight memory is used

Memory is the product here, not a feature added to a chatbot. This document explains exactly what is stored,
how it is retrieved, and what the agent does with it. Everything below is implemented in
`backend/app/services/hindsight_client.py` (the only module that talks to Hindsight),
`outcome_service.py`, `memory_service.py` and `analyzer.py`.

## One bank, tagged memories

A Hindsight bank is the unit of isolation, and there is no query across banks. So the app uses **one bank**
(`HINDSIGHT_BANK_ID`) and separates memories with tags:

| Tag | Meaning |
|---|---|
| `service:payments-api` | every memory belongs to the service; recall and reflect are scoped with it |
| `type:incident` / `type:runbook` | kind of document |
| `incident:INC-002` | the incident a fact came from |
| `runbook:RB-07` | a runbook that was used in, or is described by, the memory |
| `cause:connection_leak`, `symptom:502` | cause and symptom labels |
| `outcome:resolved` | recorded outcome |

Scoped calls use `tags_match="any_strict"` so untagged memories are never mixed in. Tags are a soft partition,
which is fine for one service. A multi-tenant product would use one bank per tenant.

## Retain

Three things are retained, each with a stable `document_id` so re-running the seed replaces instead of duplicating:

1. **Runbooks** (`scripts/seed_memory.py`): the text of the runbook plus its last-reviewed date, timestamped with
   that date.
2. **Past incidents** (`scripts/seed_memory.py`): a short postmortem paragraph starting with the incident ID, with the
   incident's original timestamp so temporal recall works ("last month", "the most recent leak").
3. **Live outcomes** (`POST /outcomes`, `outcome_service.py`): what the engineer reports after an incident.

Choices that matter:

- **`context`** labels each item ("payments-api incident postmortem"). Hindsight injects it into fact extraction,
  so it shapes what gets extracted.
- **`timestamp`** is the time the incident happened, not the time it was loaded.
- **Explicit outcomes.** Live outcomes are built by plain templating, not by an LLM. Every step gets a sentence
  such as "Scale out the service (RB-07) did not work." Outcomes are the point of this memory, so they must never
  depend on the extractor inferring them.
- **`observation_scopes="per_tag"`** asks Hindsight to consolidate evidence per tag, so a tag such as
  `cause:connection_leak` accumulates across incidents. In recall we see consolidated observations such as
  "INC-006 shared the same error signature as INC-002", which no single incident states.

## Recall (no LLM call)

`recall` runs semantic, keyword, graph and temporal retrieval and returns ranked facts quickly, with no model
call. The app uses it for the **evidence panel**:

- scoped to the service tag, up to 3000 tokens;
- facts are grouped by incident, using `document_id` for raw facts and the incident ID in the text for
  consolidated observations, which carry no `document_id`;
- each evidence card shows the recorded cause, what worked and what failed, and can expand to show the facts
  Hindsight actually remembered.

## Reflect (reasoning over memory)

`reflect` produces the recommendation. The request includes:

- the alert, wrapped in delimiters and marked as untrusted data, never instructions;
- a `response_schema` so the result is a validated object: `first_action`, `reasoning`, `avoid` (each with a reason
  and incident IDs), `supporting_incidents`, `contrasting_incidents` (similar symptom, different cause, with the
  difference) and `insufficient_precedent`;
- tag scoping to the service.

The prompt tells the model to use only what memory contains and to say when there is no precedent.

Two observations from real runs shaped the code:

- `include_facts=True` returned every recalled fact, not only the ones used, so it is **not** shown as evidence. The
  evidence panel is built from the incident IDs the recommendation names, plus recall.
- The model sometimes returns IDs like "INC-002: caused by a leak". The analyzer normalises them to bare IDs
  (covered by a test).

## What the code computes instead of the model

Anything that is a count or a date is computed from recorded outcomes in `memory_service.py`:

- runbook uses, successes and failures (for example "RB-07 worked 0 of 3");
- days since a runbook was last reviewed, and flags such as "never worked" or "not reviewed in over 6 months".

The model explains and recommends. It does not produce the numbers the screen shows.

## The before and after

The **without memory** baseline is deliberately fair: it receives the alert and the runbooks, but no incident
history. The comparison therefore shows what memory adds beyond documentation.

- On alerts that map to a runbook, the baseline usually gets the first action right (5 of 6 in our small run).
- Where memory is decisive is a lesson that lives in no runbook. In the learning test the engineer recorded that
  disabling a feature flag fixed a foreign-exchange timeout. About 8 seconds later a similar alert produced that
  recommendation with memory, while the baseline recommended scaling out both times.

## Failure handling

If reflect fails, the response falls back to recalled history with a visible warning. If Hindsight is unreachable,
the API returns a warning and does not crash. A failed retain saves nothing locally, so the app and memory never
disagree.

## Limits

Synthetic data; single-run results; reflect takes around ten seconds; no handling of a newer decision that
supersedes an older one; tags are a soft partition inside one bank.
