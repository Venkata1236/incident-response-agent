import type { AlertFields, AnalyzeResponse, OutcomeIn, OutcomeOut } from "./types";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001";

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(`Cannot reach the API at ${API_URL}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      detail = await res.text();
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const analyze = (alert: AlertFields, useMemory: boolean) =>
  post<AnalyzeResponse>("/analyze", { ...alert, use_memory: useMemory });

export const reportOutcome = (outcome: OutcomeIn) => post<OutcomeOut>("/outcomes", outcome);
