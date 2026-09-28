export type Mode = "memory" | "baseline" | "compare";

const OPTIONS: { value: Mode; label: string; hint: string }[] = [
  { value: "memory", label: "With memory", hint: "Hindsight recall and reflect" },
  { value: "baseline", label: "Without memory", hint: "Alert and runbooks only" },
  { value: "compare", label: "Compare", hint: "Both, side by side" },
];

export default function MemoryToggle({
  mode,
  onChange,
  disabled,
}: {
  mode: Mode;
  onChange: (m: Mode) => void;
  disabled?: boolean;
}) {
  return (
    <div className="segmented" role="radiogroup" aria-label="Memory mode">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={mode === o.value}
          className={mode === o.value ? "seg active" : "seg"}
          onClick={() => onChange(o.value)}
          disabled={disabled}
          title={o.hint}
        >
          <span>{o.label}</span>
          <small>{o.hint}</small>
        </button>
      ))}
    </div>
  );
}
