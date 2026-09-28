import { PRESETS } from "../presets";
import type { AlertFields } from "../types";
import MemoryToggle, { type Mode } from "./MemoryToggle";

interface Props {
  alert: AlertFields;
  onChange: (a: AlertFields) => void;
  mode: Mode;
  onMode: (m: Mode) => void;
  onAnalyze: () => void;
  busy: boolean;
}

export default function AlertPanel({ alert, onChange, mode, onMode, onAnalyze, busy }: Props) {
  const set = (k: keyof AlertFields) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    onChange({ ...alert, [k]: e.target.value });

  return (
    <section className="panel">
      <h2>Incoming alert</h2>
      <div className="chips" role="group" aria-label="Demo alerts">
        {PRESETS.map((p) => (
          <button key={p.id} className="chip" onClick={() => onChange(p.alert)} disabled={busy}>
            {p.label}
          </button>
        ))}
      </div>

      <label>
        Alert
        <input value={alert.title} onChange={set("title")} placeholder="What fired?" />
      </label>
      <label>
        Log excerpt
        <textarea rows={3} value={alert.log_excerpt} onChange={set("log_excerpt")} />
      </label>
      <label>
        Context (recent deploys or changes)
        <textarea rows={2} value={alert.context} onChange={set("context")} />
      </label>

      <MemoryToggle mode={mode} onChange={onMode} disabled={busy} />
      <button className="primary" onClick={onAnalyze} disabled={busy || alert.title.trim().length < 3}>
        {busy ? "Analyzing…" : mode === "compare" ? "Compare with and without memory" : "Analyze alert"}
      </button>
    </section>
  );
}
