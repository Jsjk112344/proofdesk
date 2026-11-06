import { stamp } from "./shared";

export type ActivityStep = {
  label: string;
  at?: string | null;
  state: "pending" | "running" | "done" | "failed";
  evidence?: unknown;
};

export function AnalystActivity({ steps }: { steps: ActivityStep[] }) {
  return <section className="panel analyst-activity" aria-label="Analyst activity">
    <h2>Analyst activity</h2>
    <ol aria-live="polite">{steps.map((step, index) => <li key={index} className={`activity-${step.state}`}>
      <span className="activity-marker" aria-hidden="true">{step.state === "done" ? "✓" : step.state === "failed" ? "!" : index + 1}</span>
      <div><strong>{step.label}</strong> <span className="muted">{step.state === "pending" ? "Waiting" : step.state === "running" ? "In progress" : step.state === "failed" ? "Stopped" : "Complete"}</span>
        {step.at && <time dateTime={step.at}>{stamp(step.at)}</time>}
        {step.evidence != null && <details><summary>Verification</summary><pre>{JSON.stringify(step.evidence, null, 2)}</pre></details>}
      </div>
    </li>)}</ol>
  </section>;
}
