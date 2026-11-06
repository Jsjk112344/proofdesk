import { useEffect, useState } from "react";
import { stamp } from "./shared";

export type ActivityStep = {
  label: string;
  at?: string | null;
  state: "pending" | "running" | "done" | "failed";
  evidence?: unknown;
};

export function AnalystActivity({ steps, active = false, shortLabels }: { steps: ActivityStep[]; active?: boolean; shortLabels?: string[] }) {
  const [expanded, setExpanded] = useState(active);
  useEffect(() => { setExpanded(active); }, [active]);
  return <section className={`analyst-activity ${expanded ? "expanded" : "compact"}`} aria-label="Analyst activity">
    <button className="activity-toggle" aria-expanded={expanded} onClick={() => setExpanded(v => !v)}>
      <span className="activity-title">Analyst activity</span>
      <span className="activity-dots">{steps.map((step, index) => <span key={index} className={`activity-${step.state}`} title={`${step.label}: ${step.state}${step.at ? ` · ${stamp(step.at)}` : ""}`}>
        <span className="activity-marker" aria-hidden="true">{step.state === "done" ? "✓" : step.state === "failed" ? "!" : index + 1}</span>
        <span>{shortLabels?.[index] || step.label}</span>
      </span>)}</span>
      <span className="activity-chevron" aria-hidden="true">{expanded ? "−" : "+"}</span>
    </button>
    {expanded && <ol aria-live="polite">{steps.map((step, index) => <li key={index} className={`activity-${step.state}`}>
      <span className="activity-marker" aria-hidden="true">{step.state === "done" ? "✓" : step.state === "failed" ? "!" : index + 1}</span>
      <div><strong>{step.label}</strong>
        {step.at && <time dateTime={step.at}>{stamp(step.at)}</time>}
      </div>
    </li>)}</ol>}
  </section>;
}
