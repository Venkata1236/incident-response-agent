import type { Recommendation as Rec } from "../types";

export default function Recommendation({ rec }: { rec: Rec }) {
  return (
    <div className="rec">
      {rec.insufficient_precedent && (
        <p className="badge neutral">No matching precedent in memory. This is a generic suggestion.</p>
      )}
      <div className="first-action">
        <span className="label">Do this first</span>
        <strong>{rec.first_action}</strong>
      </div>
      {rec.reasoning && <p className="reasoning">{rec.reasoning}</p>}

      {rec.avoid.length > 0 && (
        <div className="block avoid">
          <h4>Avoid, it already failed here</h4>
          <ul>
            {rec.avoid.map((a, i) => (
              <li key={i}>
                <strong>{a.action}</strong>
                {a.reason && <span> {a.reason}</span>}
                <span className="ids">{a.incidents.map((id) => <code key={id}>{id}</code>)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {rec.contrasting_incidents.length > 0 && (
        <div className="block contrast">
          <h4>Looks similar, but differs</h4>
          <ul>
            {rec.contrasting_incidents.map((c) => (
              <li key={c.incident}>
                <code>{c.incident}</code> <span>{c.difference}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
