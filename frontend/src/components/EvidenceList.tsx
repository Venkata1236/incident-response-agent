import { useState } from "react";
import type { EvidenceCard, EvidenceRole } from "../types";

const ROLE_LABEL: Record<EvidenceRole, string> = {
  supports: "Matches this alert",
  contrasts: "Looks similar, differs",
  related: "Also recalled",
};

function Card({ c }: { c: EvidenceCard }) {
  const [open, setOpen] = useState(false);
  return (
    <li className={`ev ${c.role}`}>
      <div className="ev-head">
        <code>{c.incident_id}</code>
        <span className={`badge role-${c.role}`}>{ROLE_LABEL[c.role]}</span>
        {c.date && <span className="muted">{c.date}</span>}
        {c.minutes_to_resolve != null && <span className="muted">{c.minutes_to_resolve} min</span>}
      </div>
      {c.summary && <p>{c.summary}</p>}
      {c.root_cause && <p><b>Cause:</b> {c.root_cause}</p>}
      {c.what_worked && <p className="ok"><b>Worked:</b> {c.what_worked}</p>}
      {c.what_failed && <p className="bad"><b>Failed:</b> {c.what_failed}</p>}
      {c.remembered_facts.length > 0 && (
        <>
          <button className="link" onClick={() => setOpen(!open)}>
            {open ? "Hide" : "Show"} what Hindsight remembered ({c.remembered_facts.length})
          </button>
          {open && (
            <ul className="facts">
              {c.remembered_facts.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          )}
        </>
      )}
    </li>
  );
}

export default function EvidenceList({ cards }: { cards: EvidenceCard[] }) {
  if (cards.length === 0) return null;
  return (
    <div className="block">
      <h4>Evidence from memory</h4>
      <ul className="evidence">{cards.map((c) => <Card key={c.incident_id} c={c} />)}</ul>
    </div>
  );
}
