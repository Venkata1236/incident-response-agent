export interface AlertFields {
  title: string;
  log_excerpt: string;
  context: string;
}

export interface AvoidItem { action: string; reason: string; incidents: string[] }
export interface Contrast { incident: string; difference: string }

export interface Recommendation {
  first_action: string;
  reasoning: string;
  avoid: AvoidItem[];
  supporting_incidents: string[];
  contrasting_incidents: Contrast[];
  insufficient_precedent: boolean;
}

export interface RunbookStat {
  runbook_id: string;
  title: string;
  uses: number;
  worked: number;
  failed: number;
  last_reviewed: string | null;
  days_since_review: number | null;
  flags: string[];
}

export type EvidenceRole = "supports" | "contrasts" | "related";

export interface EvidenceCard {
  incident_id: string;
  role: EvidenceRole;
  date: string | null;
  summary: string | null;
  root_cause: string | null;
  what_worked: string | null;
  what_failed: string | null;
  minutes_to_resolve: number | null;
  remembered_facts: string[];
}

export interface AnalyzeResponse {
  memory_used: boolean;
  recommendation: Recommendation | null;
  runbook_stats: RunbookStat[];
  evidence: EvidenceCard[];
  latency_ms: number;
  warnings: string[];
}

export interface StepResult { step: string; runbook?: string; worked: boolean }

export interface OutcomeIn extends AlertFields {
  steps: StepResult[];
  root_cause: string;
  cause_tag?: string;
  minutes_to_resolve?: number;
  resolved_by: string;
  incident_id?: string;
}

export interface OutcomeOut { incident_id: string; retained: boolean; memory_text: string; note: string }
