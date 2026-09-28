import type { AlertFields } from "./types";

/** Demo alerts. These carry only the alert itself, never the expected answers. */
export const PRESETS: { id: string; label: string; alert: AlertFields }[] = [
  {
    id: "S1",
    label: "Latency + 502s after a deploy",
    alert: {
      title: "p95 latency 4.4s and 502s rising",
      log_excerpt:
        "ERROR sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out, timeout 30.00",
      context: "Deploy v2.22 shipped 40 minutes ago.",
    },
  },
  {
    id: "S2",
    label: "502s, targets flapping, no deploy",
    alert: {
      title: "Intermittent 502s, targets flapping",
      log_excerpt:
        "target-group tg-payments-api: 2 of 4 targets unhealthy (Health checks failed: Request timed out)",
      context: "No application deploys in the last 9 days. An infrastructure change was applied to the load balancer yesterday.",
    },
  },
  {
    id: "S4",
    label: "High latency, database CPU 97%",
    alert: {
      title: "p95 latency 4.9s, database CPU 97 percent",
      log_excerpt: "RDS CPUUtilization 97% for 12 min; no connection pool errors in application logs",
      context: "A new endpoint was released this morning.",
    },
  },
];

export const RUNBOOKS: { id: string; title: string }[] = [
  { id: "RB-03", title: "Raise task memory" },
  { id: "RB-05", title: "Restart tasks" },
  { id: "RB-07", title: "Scale out the service" },
  { id: "RB-09", title: "Roll back the deploy" },
  { id: "RB-11", title: "Review ALB health checks" },
  { id: "RB-14", title: "Rotate expired certificate" },
  { id: "RB-16", title: "Fix slow query / add index" },
  { id: "RB-18", title: "Free database storage" },
];
