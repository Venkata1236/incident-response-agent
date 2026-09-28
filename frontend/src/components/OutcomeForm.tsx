import { useState } from "react";
import { reportOutcome } from "../api";
import { RUNBOOKS } from "../presets";
import type { AlertFields, OutcomeOut, StepResult } from "../types";

interface Row extends StepResult { key: number }

export default function OutcomeForm({ alert }: { alert: AlertFields }) {
  const [rows, setRows] = useState<Row[]>([]);
  const [rootCause, setRootCause] = useState("");
  const [causeTag, setCauseTag] = useState("");
  const [minutes, setMinutes] = useState("");
  const [by, setBy] = useState("on-call engineer");
  const [incidentId, setIncidentId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState<OutcomeOut | null>(null);

  const addRow = (step = "", runbook = "") =>
    setRows((r) => [...r, { key: Date.now() + r.length, step, runbook: runbook || undefined, worked: true }]);
  const patch = (key: number, p: Partial<StepResult>) =>
    setRows((r) => r.map((x) => (x.key === key ? { ...x, ...p } : x)));

  const valid = rows.length > 0 && rows.every((r) => r.step.trim().length >= 3) && rootCause.trim().length >= 3;

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const out = await reportOutcome({
        ...alert,
        steps: rows.map(({ step, runbook, worked }) => ({ step: step.trim(), runbook, worked })),
        root_cause: rootCause.trim(),
        cause_tag: causeTag.trim().toLowerCase().replace(/\s+/g, "_") || undefined,
        minutes_to_resolve: minutes ? Number(minutes) : undefined,
        resolved_by: by.trim() || "on-call engineer",
        incident_id: incidentId.trim() || undefined,
      });
      setSaved(out);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (saved) {
    return (
      <section className="panel outcome">
        <h2>Saved to memory as {saved.incident_id}</h2>
        <blockquote>{saved.memory_text}</blockquote>
        <p className="muted">{saved.note}</p>
        <button className="link" onClick={() => setSaved(null)}>Report another outcome</button>
      </section>
    );
  }

  return (
    <section className="panel outcome">
      <h2>Did it work? Teach the agent</h2>
      <p className="muted">
        Record what you tried and whether it worked. Every step is stored with an explicit outcome, so the
        next similar alert benefits.
      </p>

      <div className="chips">
        {RUNBOOKS.map((r) => (
          <button key={r.id} className="chip" onClick={() => addRow(r.title, r.id)}>+ {r.title}</button>
        ))}
        <button className="chip" onClick={() => addRow()}>+ Other step</button>
      </div>

      {rows.map((r) => (
        <div className="step-row" key={r.key}>
          <input value={r.step} onChange={(e) => patch(r.key, { step: e.target.value })} placeholder="What was done" />
          <select value={r.runbook ?? ""} onChange={(e) => patch(r.key, { runbook: e.target.value || undefined })}>
            <option value="">No runbook</option>
            {RUNBOOKS.map((b) => <option key={b.id} value={b.id}>{b.id}</option>)}
          </select>
          <button className={r.worked ? "tog yes" : "tog no"} onClick={() => patch(r.key, { worked: !r.worked })}>
            {r.worked ? "Worked" : "Did not work"}
          </button>
          <button className="link" onClick={() => setRows((x) => x.filter((y) => y.key !== r.key))} aria-label="Remove step">
            Remove
          </button>
        </div>
      ))}

      <label>
        Root cause
        <input value={rootCause} onChange={(e) => setRootCause(e.target.value)} placeholder="e.g. another connection leak introduced by v2.22" />
      </label>
      <div className="grid3">
        <label>Cause tag (optional)<input value={causeTag} onChange={(e) => setCauseTag(e.target.value)} placeholder="connection_leak" /></label>
        <label>Minutes to resolve<input type="number" min={0} value={minutes} onChange={(e) => setMinutes(e.target.value)} /></label>
        <label>Resolved by<input value={by} onChange={(e) => setBy(e.target.value)} /></label>
      </div>
      <label>
        Incident ID (optional, reuse one to overwrite while rehearsing)
        <input value={incidentId} onChange={(e) => setIncidentId(e.target.value)} placeholder="INC-011" />
      </label>

      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary" onClick={submit} disabled={!valid || busy}>
        {busy ? "Saving…" : "Save to memory"}
      </button>
    </section>
  );
}
