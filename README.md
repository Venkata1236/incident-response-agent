# Incident Response Agent

Incident response that remembers what worked.

An on-call agent built on Hindsight (Vectorize) memory. It remembers past incidents,
which fixes worked, which failed, and warns when a familiar-looking alert has a
different cause.

## Problem
During an outage the on-call engineer often repeats fixes that already failed before,
because the history lives in old tickets and people's heads.

## Solution
Retain every incident and its outcome, recall similar incidents when a new alert arrives,
and reflect to recommend the next step with cited evidence. A human makes the final call.

## How Hindsight is used
See docs/hindsight-usage.md (to be completed).

## Data
All incident data in data/incidents/ is SYNTHETIC. It is fictional and modeled on
common failure patterns seen in public postmortems. It is not real company data.

## Setup
To be completed.

## Limitations
- Synthetic data, small sample.
- Recommendations are LLM reasoning over retained history, not a trained model.
- Decision support only; a human decides.
