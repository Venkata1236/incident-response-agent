import type { RunbookStat } from "../types";

export default function RunbookStats({ stats }: { stats: RunbookStat[] }) {
  if (stats.length === 0) return null;
  return (
    <div className="block">
      <h4>Runbook track record <small>counted from recorded outcomes, not by the model</small></h4>
      <table>
        <tbody>
          {stats.map((s) => (
            <tr key={s.runbook_id}>
              <td><code>{s.runbook_id}</code> {s.title}</td>
              <td className="num">worked {s.worked} of {s.uses}</td>
              <td>
                {s.flags.map((f) => (
                  <span key={f} className="badge warn">{f}</span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
