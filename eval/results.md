# Evaluation: with and without memory

Run on 2026-09-28 17:15, 1 run(s) per variant, synthetic incident data.

**How to read this.** 'Correct' means the first action mentions the fix that worked in the recorded incidents and no failed step; it is a keyword check, so read the raw first actions below. LLM answers vary between runs, and this is a small hand-built set, not a benchmark.

- Without memory: 5/6 correct, 0 recommended a step that failed before
- With memory: 6/6 correct, 0 recommended a step that failed before

| Alert | Variant | Run | Mode | Correct | Recommends failed step | First action |
|---|---|---|---|---|---|---|
| S1 | full alert | 1 | baseline | yes | no | Redeploy the previous ECS task definition revision (RB-09 Roll back a deploy) to revert the v2.22 changes. |
| S1 | full alert | 1 | memory | yes | no | Immediately perform a rollback to the previous version of the payments-api using runbook RB-09. |
| S1 | no deploy hint | 1 | baseline | no | no | Investigate slow queries and missing indexes (Runbook RB-16). |
| S1 | no deploy hint | 1 | memory | yes | no | Roll back the service to the previous version using RB-09. |
| S2 | full alert | 1 | baseline | yes | no | Investigate ALB target health (RB-11): compare target group health check settings with service behavior and review recent load balancer changes. |
| S2 | full alert | 1 | memory | yes | no | Investigate ALB health check configuration and status per RB-11. |
| S2 | less leading | 1 | baseline | yes | no | Investigate ALB target health per RB-11: compare the target group health check path, timeout, and thresholds against the service's response under load, and review recent infrastructure changes. |
| S2 | less leading | 1 | memory | yes | no | Investigate Application Load Balancer (ALB) health check configurations per runbook RB-11. |
| S4 | full alert | 1 | baseline | yes | no | Investigate slow queries and missing indexes in the RDS instance (Runbook RB-16). |
| S4 | full alert | 1 | memory | yes | no | Use RB-16 to investigate the database performance and check for slow queries or missing indexes related to the new endpoint. |
| S4 | no context | 1 | baseline | yes | no | Investigate slow queries in RDS Performance Insights and address any missing indexes (Runbook RB-16). |
| S4 | no context | 1 | memory | yes | no | Investigate RDS performance insights for slow queries and apply missing indexes using RB-16. |
