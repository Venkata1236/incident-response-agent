import { useEffect, useRef, useState } from "react";
import { analyze } from "./api";
import AlertPanel from "./components/AlertPanel";
import type { Mode } from "./components/MemoryToggle";
import OutcomeForm from "./components/OutcomeForm";
import ResultColumn, { type RunState } from "./components/ResultColumn";
import { PRESETS } from "./presets";
import type { AlertFields } from "./types";

const IDLE: RunState = { status: "idle", elapsed: 0 };

export default function App() {
  const [alert, setAlert] = useState<AlertFields>(PRESETS[0].alert);
  const [mode, setMode] = useState<Mode>("memory");
  const [withMemory, setWithMemory] = useState<RunState>(IDLE);
  const [baseline, setBaseline] = useState<RunState>(IDLE);
  const timers = useRef<number[]>([]);

  useEffect(() => () => timers.current.forEach(window.clearInterval), []);

  const run = async (useMemory: boolean, set: React.Dispatch<React.SetStateAction<RunState>>) => {
    const started = Date.now();
    set({ status: "loading", elapsed: 0 });
    const tick = window.setInterval(
      () => set((s) => (s.status === "loading" ? { ...s, elapsed: Math.round((Date.now() - started) / 1000) } : s)),
      1000
    );
    timers.current.push(tick);
    try {
      const data = await analyze(alert, useMemory);
      set({ status: "done", data, elapsed: 0 });
    } catch (e) {
      set({ status: "error", error: e instanceof Error ? e.message : String(e), elapsed: 0 });
    } finally {
      window.clearInterval(tick);
    }
  };

  const onAnalyze = () => {
    if (mode === "memory" || mode === "compare") void run(true, setWithMemory);
    if (mode === "baseline" || mode === "compare") void run(false, setBaseline);
  };

  const busy = withMemory.status === "loading" || baseline.status === "loading";
  const showBaseline = mode === "baseline" || mode === "compare";
  const showMemory = mode === "memory" || mode === "compare";
  const memoryDone = withMemory.status === "done";

  return (
    <div className="app">
      <header className="top">
        <div>
          <h1>Incident Response Agent</h1>
          <p>Incident response that remembers what worked.</p>
        </div>
        <span className="badge neutral" title="All incidents are fictional and modeled on public postmortem patterns">
          Synthetic data
        </span>
      </header>

      <main>
        <AlertPanel alert={alert} onChange={setAlert} mode={mode} onMode={setMode} onAnalyze={onAnalyze} busy={busy} />

        <div className={showBaseline && showMemory ? "results two" : "results"}>
          {showBaseline && (
            <ResultColumn
              title="Without memory"
              subtitle="Sees only the alert and the runbooks"
              state={baseline}
              accent="baseline"
            />
          )}
          {showMemory && (
            <ResultColumn
              title="With memory"
              subtitle="Hindsight recall and reflect over past incidents"
              state={withMemory}
              accent="memory"
            />
          )}
        </div>

        {memoryDone && <OutcomeForm alert={alert} />}
      </main>
    </div>
  );
}
