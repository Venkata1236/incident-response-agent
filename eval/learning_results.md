# Learning test: a lesson that exists in no runbook

Run on 2026-09-28 17:23 against a synthetic bank.

```
STEP 1: interaction 1, a failure type memory has not seen
  without memory: Scale out the ECS service by increasing the desired task count from 4 to 8 (run RB-07) to address the high latency and timeouts.
  with memory:    Investigate RDS performance insights and slow query logs for the rates-service calls, as per the principles in RB-16.

STEP 2: the engineer records what actually fixed it (a fix that is in no runbook)
  retained as INC-011

STEP 3: interaction 2, a similar alert. Polling until memory uses the lesson
  +  8s  learned=YES  Disable the fx_live_rates feature flag to force the service to use cached FX rates.

STEP 4: the same similar alert without memory
  without memory: Increase the ECS desired task count from 4 to 8 (RB-07) and monitor latency.

RESULT
  Memory used the new lesson about 8s after it was recorded.
  With memory: Disable the fx_live_rates feature flag to force the service to use cached FX rates.
  Without memory: Increase the ECS desired task count from 4 to 8 (RB-07) and monitor latency.
```
