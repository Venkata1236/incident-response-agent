import type { AnalyzeResponse } from "../types";
import EvidenceList from "./EvidenceList";
import Recommendation from "./Recommendation";
import RunbookStats from "./RunbookStats";

export interface RunState {
  status: "idle" | "loading" | "done" | "error";
  data?: AnalyzeResponse;
  error?: string;
  elapsed: number;
}

interface Props {
  title: string;
  subtitle: string;
  state: RunState;
  accent: "memory" | "baseline";
}

export default function ResultColumn({ title, subtitle, state, accent }: Props) {
  return (
    <section className={`panel result ${accent}`}>
      <header>
        <h2>{title}</h2>
        <p className="muted">{subtitle}</p>
      </header>

      {state.status === "idle" && <p className="empty">Run an analysis to see the recommendation here.</p>}

      {state.status === "loading" && (
        <div className="loading" role="status">
          <div className="spinner" />
          <p>
            {accent === "memory"
              ? "Hindsight is recalling and reflecting over past incidents. This usually takes 10 to 20 seconds."
              : "Asking the model with the alert and runbooks only."}
          </p>
          <p className="muted">{state.elapsed}s</p>
        </div>
      )}

      {state.status === "error" && <p className="error" role="alert">{state.error}</p>}

      {state.status === "done" && state.data && (
        <>
          {state.data.warnings.map((w) => (
            <p key={w} className="banner warn" role="alert">{w}</p>
          ))}
          {state.data.recommendation ? (
            <Recommendation rec={state.data.recommendation} />
          ) : state.data.warnings.length === 0 ? (
            <p className="empty">No recommendation was produced.</p>
          ) : null}
          <RunbookStats stats={state.data.runbook_stats} />
          <EvidenceList cards={state.data.evidence} />
          <p className="muted foot">{(state.data.latency_ms / 1000).toFixed(1)}s</p>
        </>
      )}
    </section>
  );
}