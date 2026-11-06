import { AnalystActivity, type ActivityStep } from "./activity";
import { useEffect, useRef, useState } from "react";
import { api, Badge, Empty, newId, post, shortCopy, stamp, time } from "./shared";

export type Arm = {
  id: string;
  label: string;
  n: number;
  visits: number;
  conversions: number;
  buyers: number;
  spend_cents: number;
  spend_usd: string;
  conversion_rate: number | null;
  visit_rate: number | null;
  spend_per_customer_usd: string | null;
};
export type Dataset = {
  id: string;
  synthetic: boolean;
  source: {
    title: string;
    publisher: string;
    download_url: string;
    description_url: string;
    catalog_url: string;
    checksum_reference_url: string;
    study_period: string;
    rights: string;
  };
  raw: { sha256: string; bytes: number; rows: number; columns: string[] };
  importer_version: string;
  imported_at: string;
  analysis_input: { format: string; sha256: string; bytes: number; columns: string[] };
  row_identifier: string;
  arms: Arm[];
  validation: { rows_validated: number; rejections: number; checks: string[]; observed: Record<string, number>; currency: string };
  limitations: string[];
};
export type PlanSpec = {
  title: string;
  question: string;
  dataset_id: string;
  dataset_raw_sha256: string;
  comparison: { treatment: string; control: string };
  primary_outcome: string;
  secondary_outcomes: string[];
  confidence_level: number;
  bootstrap: { seed: number; resamples: number };
  exploratory_breakdowns: string[];
  retrospective: boolean;
  preregistered: boolean;
};
export type Plan = { id: string; dataset_id: string; version: number; sha256: string; spec: PlanSpec; created_at: string };
export type PlanSummary = {
  id: string;
  version: number;
  sha256: string;
  dataset_id: string;
  title: string;
  question: string;
  comparison: { treatment: string; control: string };
  created_at: string;
  runs: number;
  latest_run: {
    id: string;
    status: string;
    failure_reason: string | null;
    finished_at: string | null;
    interpretation_status: string | null;
    interpretation_provenance: string | null;
  } | null;
  proposal_version: number;
  tasks: string[];
  active_jobs: number;
};
export type Metric = {
  id: string;
  label: string;
  definition: string;
  kind: string;
  value: number | string | null;
  unit: string | null;
  interval: [number, number] | null;
  interval_method: string | null;
  level: number | null;
  denominator: Record<string, number> | null;
  path: string | null;
  exploratory: boolean;
  provenance: string;
};
export type Reading = {
  question_answered: string;
  interpretation: string;
  alternative_explanations: string[];
  unknowns: string[];
  proposed_next_experiment: Record<string, string | string[]>;
};
export type Interpretation = {
  status: string;
  provenance: string;
  label: string;
  failure_reason?: string;
  created_at: string;
  rendered: Reading | null;
};
export type Execution = {
  id: string;
  status: string;
  failure_reason: string | null;
  exit_code: number | null;
  scenario: string;
  limits: Record<string, number>;
  cleanup: { removed: boolean; reason: string | null };
  validated_artifacts: { sha256: string; validation: string; size_bytes: number }[];
  image: string | null;
  input_sha256: string | null;
  script_sha256: string | null;
  started_at: string;
  finished_at: string | null;
  runtime: Record<string, string> | null;
  task_elapsed_seconds: number | null;
  log: string | null;
  unavailable?: string;
};
export type Run = {
  id: string;
  plan_version: number;
  plan_sha256: string;
  job_id: string;
  attempt: number;
  status: string;
  created_at: string;
  finished_at: string | null;
  failure_reason: string | null;
  execution_id: string | null;
  artifact_id: string | null;
  program_sha256: string | null;
  input_sha256: string | null;
  reconciliation: { status: string; checks: Record<string, string>[]; independent_implementation: string } | null;
  metrics: Metric[] | null;
  interpretation: Interpretation | null;
  generation: {
    mode: string | null;
    model: string | null;
    receipts: Record<string, string>;
    diagnostics: Record<string, unknown>[];
    budget?: Record<string, string | number>;
    usage?: Record<string, Record<string, number>>;
    reservation?: Record<string, Record<string, number | string>>;
  } | null;
  execution: Execution | null;
};
export type ProposalContent = {
  hypothesis: string;
  variant_a: string;
  variant_b: string;
  audience_requirements: string[];
  unit_of_randomization: string;
  primary_outcome: string;
  observation_window: string;
  decision_rule: string;
  missing_inputs: string[];
  scenario_assumptions: { audience_size: number | null; gross_margin: number | null; campaign_cost_usd: string | null };
  sample_size_inputs: { minimum_detectable_pp: number | null; alpha: number | null; power: number | null };
  notes: string;
};
export type Proposal = { id: string; plan_id: string; run_id: string; version: number; sha256: string; content: ProposalContent; provenance: string; created_at: string };
export type Task = {
  id: string;
  plan_id: string;
  run_id: string;
  proposal_id: string;
  proposal_version: number;
  proposal_sha256: string;
  title: string;
  assignee_label: string;
  proposed_action: string;
  due_date: string | null;
  status: string;
  approval: Record<string, string | number> | null;
  job_id: string | null;
  packet_artifact_id: string | null;
  completion: Record<string, string> | null;
  created_at: string;
  updated_at: string;
  events: { stage: string; at: string; note?: string }[];
};
export type Job = {
  id: string;
  kind: string;
  plan_id: string;
  plan_version: number;
  task_id: string | null;
  payload: Record<string, string>;
  payload_sha256: string;
  due_at: string;
  status: string;
  attempts: number;
  max_attempts: number;
  lease_until: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  failure_reason: string | null;
  outcome: Record<string, unknown> | null;
  events: { stage: string; at: string; [key: string]: unknown }[];
};
export type Overview = {
  datasets: Dataset[];
  plans: PlanSummary[];
  tasks: Task[];
  jobs: Job[];
  generation_mode: string;
  public_demo: boolean;
  limits: Record<string, number>;
  scheduler: { last_error: string | null; lease_seconds: number };
};
export type PlanDetail = {
  plan: Plan;
  dataset: Dataset;
  runs: Run[];
  proposals: Proposal[];
  tasks: Task[];
  jobs: Job[];
  generation_mode: string;
  program_sha256: string;
};
type Packet = {
  packet: {
    status: string;
    what_this_is: string;
    unresolved_inputs: string[];
    external_prerequisites: string[];
    readiness_checks: { input: string; label: string; status: string; value: unknown; note?: string }[];
    scenario: Record<string, unknown>;
    sample_size: Record<string, unknown>;
    not_claimed: string[];
    bindings: Record<string, string | number>;
  };
  markdown: string;
};

export type Route =
  | { name: "home"; key: string }
  | { name: "new"; key: string }
  | { name: "experiment"; id: string; key: string }
  | { name: "queue"; key: string }
  | { name: "prospects"; key: string };

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "") || "/";
  if (path === "/prospects") return { name: "prospects", key: path };
  if (path === "/queue") return { name: "queue", key: path };
  if (path === "/experiments/new") return { name: "new", key: path };
  const match = path.match(/^\/experiments\/([a-f0-9]{32})$/);
  if (match) return { name: "experiment", id: match[1], key: path };
  return { name: "home", key: "/" };
}
export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(location.hash));
  useEffect(() => {
    const listener = () => setRoute(parseRoute(location.hash));
    window.addEventListener("hashchange", listener);
    return () => window.removeEventListener("hashchange", listener);
  }, []);
  return route;
}
export const go = (path: string) => {
  location.hash = path;
};

export const ACTIVE_JOB = ["scheduled", "running"];
const TASK_LABELS: Record<string, string> = {
  pending_review: "Awaiting approval",
  approved: "Approved",
  scheduled: "Scheduled",
  running: "Running",
  ready_for_review: "Ready for review",
  completed: "Completed",
  cancelled: "Cancelled",
  failed: "Failed",
};
const TONES: Record<string, string> = {
  pending_review: "warn",
  approved: "info",
  scheduled: "info",
  running: "running",
  ready_for_review: "ok",
  completed: "ok",
  cancelled: "muted",
  failed: "failed",
  succeeded: "ok",
};
const PROVENANCE: Record<string, { label: string; detail: string }> = {
  deterministic: {
    label: "Analyst: Rule-based",
    detail: "Controller text built from the interval positions of validated metrics. No model request was made.",
  },
  live_model: {
    label: "Analyst: Qwen 3.8 on Vultr Inference",
    detail: "The Vultr model proposed this reading from validated aggregate metrics; every number was rendered by the controller from metric ids, and the text was checked for raw numbers, ROI wording and actions against the historical records, not for truth.",
  },
  saved_replay: { label: "Analyst: Qwen 3.8 on Vultr Inference", detail: "cached response: a previously accepted live response for identical inputs; no new request was made." },
  human_edited: { label: "Edited by you", detail: "You changed this version." },
  failed: { label: "Analyst unavailable", detail: "The AI reading failed; validated statistics are preserved." },
};

export const pct = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined ? "undefined" : `${(value * 100).toFixed(digits)}%`;
const pp = (value: number) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}`;
const usd = (cents: number | null | undefined, signed = false) => {
  if (cents === null || cents === undefined) return "undefined";
  const rounded = Math.round(cents);
  const text = `$${(Math.abs(rounded) / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return rounded < 0 ? `-${text}` : signed ? `+${text}` : text;
};
const num = (value: number) => value.toLocaleString("en-US");

export function formatMetric(m: Metric): string {
  const v = m.value;
  if (v === null || v === undefined) return "undefined (empty group)";
  if (m.kind === "text") return String(v);
  if (m.kind === "count") return num(v as number);
  const d = m.denominator || {};
  if (m.kind === "rate") {
    let text = pct(v as number);
    if ("events" in d) text += ` (${num(d.events)} of ${num(d.n)})`;
    if (m.interval) text += `; 95% CI ${pct(m.interval[0])} to ${pct(m.interval[1])}`;
    return text;
  }
  if (m.kind === "difference_pp") {
    let text = `${pp(v as number)} percentage points`;
    if (m.interval) text += ` (95% CI ${pp(m.interval[0])} to ${pp(m.interval[1])})`;
    return text;
  }
  if (m.kind === "relative_percent") return `${(v as number) >= 0 ? "+" : ""}${pct(v as number)}`;
  if (m.kind === "currency") {
    let text = usd(v as number);
    if (d.n && m.id.endsWith("spend_total")) text += ` across ${num(d.n)} assigned customers`;
    else if (d.n) text += ` per assigned customer (${num(d.n)} customers, zero spend included)`;
    return text;
  }
  if (m.kind === "currency_difference") {
    let text = `${usd(v as number, true)} per assigned customer`;
    if (m.interval) text += ` (95% bootstrap CI ${usd(m.interval[0], true)} to ${usd(m.interval[1], true)})`;
    return text;
  }
  return String(v);
}

function byId(metrics: Metric[] | null) {
  return Object.fromEntries((metrics || []).map((m) => [m.id, m])) as Record<string, Metric>;
}

export function taskLabel(status: string) {
  return TASK_LABELS[status] || status;
}

function ProvenanceBadge({ provenance }: { provenance: string }) {
  return <Badge tone={provenance}>{PROVENANCE[provenance]?.label || provenance}</Badge>;
}

// ---------------------------------------------------------------- Home / overview
export function ExperimentsHome({ overview }: { overview: Overview }) {
  const [opening, setOpening] = useState(false);
  const verificationDialog = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  async function openCampaign() {
    const benchmark = [...overview.plans].reverse().find(p => p.dataset_id === "hillstrom-2008" && p.title === "Mens e-mail versus no e-mail") || overview.plans[0];
    if (benchmark) return go(`/experiments/${benchmark.id}`);
    setOpening(true);
    try {
      const plan = await post<Plan>("/api/experiments/plans", {
        dataset_id: overview.datasets[0]?.id, title: "Mens e-mail versus no e-mail",
        question: "Did these e-mails create additional purchases, and what should we test next?",
        comparison: { treatment: "mens_email", control: "no_email" },
        bootstrap: { seed: 20080320, resamples: 2000 },
        exploratory_breakdowns: ["newbie", "channel"], request_id: newId(),
      });
      go(`/experiments/${plan.id}`);
    } catch (e) { setError((e as Error).message); }
    finally { setOpening(false); }
  }
  const analysed = overview.plans.filter(p => p.latest_run?.status === "succeeded").length;
  const awaiting = overview.plans.filter(p => p.proposal_version > 0 &&
    !overview.tasks.some(t => t.plan_id === p.id && t.proposal_version === p.proposal_version && ["approved", "scheduled", "running", "ready_for_review", "completed"].includes(t.status))).length;
  return <>
    <div className="heading home-hero">
      <h1>Sell more: Your AI sales analyst</h1>
      <p className="lede">Understand your last campaign, choose the next move, and return to work prepared on Vultr.</p>
    </div>
    {error && <p className="alert" role="alert">{error}</p>}
    <div className="two entry-doors">
      <section className="panel entry-door">
        <h2>Have past campaigns? See what worked.</h2>
        <p>Find the result, understand the uncertainty and choose your next move.</p>
        <button className="primary" disabled={opening || !overview.datasets.length} onClick={() => void openCampaign()}>
          {opening ? "Opening…" : "Analyse a campaign"}
        </button>
        <p className="hint">Explore a real campaign.</p>
      </section>
      <section className="panel entry-door">
        <h2>Starting from zero? Let's find your first customers.</h2>
        <p>Research a prospect and return to an evidence-backed brief and a draft ready for your approval.</p>
        <a className="secondary button-link" href="#/prospects">Research a prospect</a>
        <p className="hint">Start with an example prospect.</p>
      </section>
    </div>
    <div className="metric-grid dashboard-stats">
      <Stat label="Campaigns analysed" value={String(analysed)} />
      <Stat label="Next moves awaiting approval" value={String(awaiting)} />
      <Stat label="Ready for review" value={String(overview.tasks.filter(t => t.status === "ready_for_review").length)} />
      <Stat label="Analyst" value={(PROVENANCE[overview.plans[0]?.latest_run?.interpretation_provenance || overview.generation_mode]?.label || overview.generation_mode).replace("Analyst: ", "")} />
    </div>
    <button className="link-button page-verification-link" onClick={() => verificationDialog.current?.showModal()}>Verification</button>
    <dialog ref={verificationDialog} aria-label="Verification" className="verification-dialog">
      <button className="secondary dialog-close" onClick={() => verificationDialog.current?.close()}>Close</button>
      {overview.datasets[0] && <DatasetCard dataset={overview.datasets[0]} />}
    </dialog>
  </>;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function DatasetCard({ dataset, compact = false }: { dataset: Dataset; compact?: boolean }) {
  return (
    <section className="panel" aria-labelledby="dataset-heading">
      <h2 id="dataset-heading">
        Source dataset <Badge tone={dataset.synthetic ? "synthetic" : "ok"}>{dataset.synthetic ? "Synthetic fixture" : "Public benchmark"}</Badge>
      </h2>
      <p>
        <strong>{dataset.source.title}</strong> · {dataset.source.publisher}.{" "}
        <a href={dataset.source.description_url} target="_blank" rel="noreferrer noopener">
          Publisher description
        </a>{" "}
        ·{" "}
        <a href={dataset.source.catalog_url} target="_blank" rel="noreferrer noopener">
          Catalog entry
        </a>
      </p>
      <p className="muted">{dataset.source.study_period}</p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Original arm</th>
              <th>Customers assigned</th>
              <th>Visits</th>
              <th>Purchases</th>
              <th>Purchase rate</th>
              <th>Spend (USD)</th>
              <th>Spend per customer</th>
            </tr>
          </thead>
          <tbody>
            {dataset.arms.map((arm) => (
              <tr key={arm.id}>
                <td>{arm.label}</td>
                <td>{num(arm.n)}</td>
                <td>{num(arm.visits)}</td>
                <td>{num(arm.conversions)}</td>
                <td>{pct(arm.conversion_rate)}</td>
                <td>{Number(arm.spend_usd).toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                <td>${arm.spend_per_customer_usd}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted">
        {num(dataset.raw.rows)} rows validated, {dataset.validation.rejections} rejections · raw SHA-256{" "}
        <span className="hash">{dataset.raw.sha256.slice(0, 16)}…</span> · importer {dataset.importer_version} · imported{" "}
        {stamp(dataset.imported_at)}. Raw rows stay on the server and are never served; only aggregates and
        the sandboxed analysis use them.
      </p>
      {!compact && (
        <>
          <details className="verification"><summary>Source context</summary><h3>Limitations recorded with the import</h3>
          <ul className="plain">
            {dataset.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
          <h3>Validation</h3>
          <ul className="plain">
            {dataset.validation.checks.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
            <li>{dataset.validation.currency}</li>
            <li>
              Observed consistency: {dataset.validation.observed.conversion_without_spend} conversions without spend,{" "}
              {dataset.validation.observed.spend_without_conversion} spend rows without conversion.
            </li>
          </ul>
          <p className="muted">{dataset.row_identifier}</p>
          <p className="muted">Rights: {dataset.source.rights}</p></details>
        </>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- New plan
export function NewPlanForm({ overview, onCreated, onError }: { overview: Overview; onCreated: () => Promise<void>; onError: (m: string) => void }) {
  const dataset = overview.datasets[0];
  const [title, setTitle] = useState("Mens e-mail versus no e-mail");
  const [question, setQuestion] = useState("Did these e-mails create additional purchases, and what should we test next?");
  const [treatment, setTreatment] = useState("mens_email");
  const [control, setControl] = useState("no_email");
  const [seed, setSeed] = useState("20080320");
  const [resamples, setResamples] = useState("2000");
  const [breakdowns, setBreakdowns] = useState<string[]>(["newbie", "channel"]);
  const [saving, setSaving] = useState(false);
  const requestId = useRef<string | null>(null);
  if (!dataset) return <Empty title="No dataset imported." text="Import the pinned benchmark first." />;
  const arms = dataset.arms;
  async function save(e: React.FormEvent) {
    e.preventDefault();
    onError("");
    setSaving(true);
    requestId.current ||= newId();
    try {
      const plan = await post<Plan>("/api/experiments/plans", {
        dataset_id: dataset!.id,
        title,
        question,
        comparison: { treatment, control },
        bootstrap: { seed: Number(seed), resamples: Number(resamples) },
        exploratory_breakdowns: breakdowns,
        request_id: requestId.current,
      });
      requestId.current = null;
      await onCreated();
      go(`/experiments/${plan.id}`);
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }
  return (
    <>
      <div className="heading">
        <h1>Save an analysis plan</h1>
        <p className="lede">Choose the campaign arms and save your question.</p>
      </div>
      <div className="landing-grid">
        <form className="panel compose" onSubmit={(e) => void save(e)}>
          <label htmlFor="plan-title">Plan title</label>
          <input id="plan-title" type="text" value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} />
          <label htmlFor="plan-question">Question</label>
          <input id="plan-question" type="text" value={question} maxLength={300} onChange={(e) => setQuestion(e.target.value)} />
          <div className="two">
            <div>
              <label htmlFor="plan-treatment">Treatment arm</label>
              <select id="plan-treatment" value={treatment} onChange={(e) => setTreatment(e.target.value)}>
                {arms.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.label} ({num(a.n)} customers)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="plan-control">Control arm</label>
              <select id="plan-control" value={control} onChange={(e) => setControl(e.target.value)}>
                {arms.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.label} ({num(a.n)} customers)
                  </option>
                ))}
              </select>
            </div>
          </div>
          <details className="disclosure"><summary>Comparison details</summary><p className="hint">
            The third arm stays visible in the source overview but is excluded from this comparison.
            Original assignment is never changed; only original arms can be compared.
          </p></details>
          <div className="two">
            <div>
              <label htmlFor="plan-seed">Bootstrap seed</label>
              <input id="plan-seed" type="text" inputMode="numeric" value={seed} onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))} />
            </div>
            <div>
              <label htmlFor="plan-resamples">Bootstrap resamples</label>
              <select id="plan-resamples" value={resamples} onChange={(e) => setResamples(e.target.value)}>
                <option value="1000">1,000</option>
                <option value="2000">2,000</option>
                <option value="4000">4,000</option>
              </select>
            </div>
          </div>
          <fieldset className="checks-field">
            <legend>Exploratory breakdowns (descriptive only)</legend>
            {["newbie", "channel"].map((b) => (
              <label key={b} className="inline">
                <input
                  type="checkbox"
                  checked={breakdowns.includes(b)}
                  onChange={(e) =>
                    setBreakdowns((all) => (e.target.checked ? [...all, b] : all.filter((x) => x !== b)))
                  }
                />{" "}
                {b === "newbie" ? "New versus existing customers" : "Acquisition channel"}
              </label>
            ))}
          </fieldset>
          <details className="disclosure"><summary>Analysis methods</summary><p className="hint">
            Fixed by the plan: primary outcome purchase conversion per assigned customer; secondary outcomes
            visits and spend per assigned customer (zero spend included); 95% Wilson and Newcombe intervals;
            seeded customer-level bootstrap for spend.
          </p></details>
          <div className="compose-actions">
            <button className="primary" type="submit" disabled={saving || !title.trim() || !question.trim() || treatment === control}>
              {saving ? "Saving…" : "Save plan"}
            </button>
            <a className="secondary button-link" href="#/">
              Cancel
            </a>
          </div>
        </form>
        <details className="verification"><summary>Verification</summary>        <p className="lede">
          Fix the comparison before anything runs. This is a retrospective re-analysis of a published
          benchmark: the arm counts were inspected before this product existed, so the plan is saved for
          reproducibility, not as a preregistration.
        </p><DatasetCard dataset={dataset} /></details>
      </div>
    </>
  );
}

// ---------------------------------------------------------------- Experiment detail
export function ExperimentView({ planId, onChanged, onError }: { planId: string; onChanged: () => Promise<void>; onError: (m: string) => void }) {
  const [detail, setDetail] = useState<PlanDetail | null>(null);
  const [running, setRunning] = useState(false);
  const [proposalDirty, setProposalDirty] = useState(false);
  const [missing, setMissing] = useState(false);
  const requestId = useRef<string | null>(null);
  async function load() {
    try {
      const next = await api<PlanDetail>(`/api/experiments/plans/${planId}`);
      setDetail(next);
      return next;
    } catch (e) {
      if ((e as Error).message.includes("does not exist")) setMissing(true);
      else onError((e as Error).message);
      return null;
    }
  }
  useEffect(() => {
    setDetail(null);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);
  const activeJobs = detail?.jobs.filter((j) => ACTIVE_JOB.includes(j.status)).length || 0;
  useEffect(() => {
    if (!detail || activeJobs === 0) return;
    const timer = window.setTimeout(async () => {
      const next = await load();
      if (next && next.jobs.filter((j) => ACTIVE_JOB.includes(j.status)).length === 0) await onChanged();
    }, 1200);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail, activeJobs]);
  if (missing) return <Empty title="This analysis is not in your session." text="Another session's records are not visible here." />;
  if (!detail)
    return (
      <p className="loading" role="status">
        Opening the analysis…
      </p>
    );
  const run = detail.runs.find((r) => r.status === "succeeded") || detail.runs[0] || null;
  const latest = detail.runs[0] || null;
  const proposal = detail.proposals[0] || null;
  const analysisJob = detail.jobs.find(j => j.kind === "analyze_plan");
  const task = detail.tasks.find(t => t.proposal_sha256 === proposal?.sha256 && t.status !== "cancelled");
  const preparation = task ? detail.jobs.find(j => j.kind === "prepare_packet" && j.task_id === task.id) : undefined;
  const activityRun = detail.runs.find(r => r.job_id === analysisJob?.id);
  const approvedCurrent = task?.approval && task.proposal_sha256 === proposal?.sha256;
  const event = (stage: string) => analysisJob?.events.find(e => e.stage === stage)?.at;
  const steps: ActivityStep[] = [
    { label: "Picked up by SalesDesk worker on Vultr", at: event("claimed"), state: event("claimed") ? "done" : "pending" },
    { label: "Running the numbers", at: event("executing"), state: activityRun?.reconciliation ? "done" : event("executing") ? (analysisJob?.status === "failed" ? "failed" : "running") : "pending", evidence: activityRun?.execution },
    { label: "Results verified", at: event("interpreting"), state: activityRun?.reconciliation ? "done" : "pending", evidence: activityRun?.reconciliation },
    { label: `Reading the result (Vultr Inference · ${activityRun?.generation?.model || "waiting for model"})`, at: activityRun?.interpretation?.created_at || event("interpreting"), state: activityRun?.interpretation?.status === "succeeded" ? "done" : activityRun?.interpretation?.status === "failed" ? "failed" : event("interpreting") ? "running" : "pending", evidence: activityRun?.generation },
    { label: "Next move drafted", at: proposal?.created_at, state: proposal ? "done" : "pending", evidence: proposal ? { sha256: proposal.sha256, version: proposal.version } : undefined },
    { label: "Awaiting your approval", at: approvedCurrent ? String(task!.approval!.approved_at) : proposal?.created_at, state: approvedCurrent ? "done" : proposal ? "running" : "pending", evidence: task?.approval },
    { label: "Preparing your packet", at: preparation?.started_at || preparation?.due_at, state: task?.packet_artifact_id ? "done" : preparation?.status === "failed" ? "failed" : preparation ? "running" : "pending" },
    { label: "Ready for review", at: preparation?.finished_at, state: task?.packet_artifact_id ? "done" : "pending", evidence: task?.packet_artifact_id },
  ];
  async function runNow() {
    onError("");
    setRunning(true);
    requestId.current ||= newId();
    try {
      await post<Job>(`/api/experiments/plans/${planId}/runs`, { request_id: requestId.current });
      requestId.current = null;
      await load();
      await onChanged();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }
  const working = activeJobs > 0;
  const metrics = byId(run?.metrics || null);
  const reading = run?.interpretation?.rendered;
  const analystHeadline = reading?.question_answered.endsWith("?") && metrics["treatment.conversion_rate"] && metrics["control.conversion_rate"]
    ? `${metrics["design.treatment_label"].value} recorded a ${pct(metrics["treatment.conversion_rate"].value as number)} purchase rate versus ${pct(metrics["control.conversion_rate"].value as number)} for ${metrics["design.control_label"].value}.`
    : reading?.question_answered;
  const takeaway = analystHeadline?.replace(/, with a difference of[\s\S]*$/i, ".") ||
    (run?.interpretation?.status === "failed" ? "The numbers are ready; the analyst reading failed." : "Your campaign answer will appear here.");
  return (
    <>
      <div className="prospect-head campaign-title">
        <h1>{detail.plan.spec.title}</h1>
        <button className={run ? "secondary" : "primary"} onClick={() => void runNow()} disabled={running || working}>
          {detail.runs.length ? "Run analysis again" : "Run analysis now"}
        </button>
      </div>
      <AnalystActivity steps={steps} active={working} shortLabels={["Pickup", "Analyse", "Verify", "Read", "Propose", "Approve", "Prepare", "Ready"]} />
      {latest && latest.status === "failed" && (
        <div className="alert" role="alert">
          <strong>The latest run failed.</strong> Reason <span className="code">{latest.failure_reason}</span>. Earlier
          successful results stay available; nothing was retried automatically beyond the bounded job retry.
        </div>
      )}
      {run?.interpretation?.status === "failed" && (
        <div className="alert" role="alert">
          <strong>The AI interpretation step failed</strong> (<span className="code">{run.interpretation.failure_reason}</span>
          ). The statistical result below is unchanged; Details are under Verification.
        </div>
      )}
      <section aria-label="Answer" className="panel answer-card">
        <div className="answer-heading">
          <h2 className="answer-takeaway" title={reading?.question_answered}>{shortCopy(takeaway, 22)}</h2>
          {run?.interpretation && <ProvenanceBadge provenance={run.interpretation.status === "failed" ? "failed" : run.interpretation.provenance} />}
        </div>
        {run?.metrics && <div className="answer-numbers">{["treatment", "control"].map(arm => {
          const rate = metrics[`${arm}.conversion_rate`];
          return rate && <div key={arm}>
            <span>{String(metrics[`design.${arm}_label`]?.value || arm)}</span>
            <strong>{pct(rate.value as number)}</strong>
            <small>of {num(rate.denominator?.n || 0)}</small>
          </div>;
        })}</div>}
        {proposal && <p className="answer-next" title={proposal.content.hypothesis}><strong>Next move:</strong> {shortCopy(proposal.content.hypothesis, 16)}</p>}
        {run && <TaskPanel detail={detail} proposal={proposal} dirty={proposalDirty} onChange={async () => { await load(); await onChanged(); }} onError={onError} />}
      </section>
      {run?.metrics && <section className="panel purchase-chart" aria-label="Purchase rates">
        <RateChart title="Purchase rate by original arm" metrics={[metrics["treatment.conversion_rate"], metrics["control.conversion_rate"]].filter(Boolean)} caption="95% Wilson score intervals." />
      </section>}
      <details className="full-analysis disclosure"><summary>See full analysis</summary>
        <InterpretationTab run={run} working={working} />
        <ResultsTab detail={detail} run={run} working={working} />
      </details>
      <section aria-label="Next move">
        <NextActionTab detail={detail} run={run} proposal={proposal} onDirty={setProposalDirty} onChange={async () => {
          await load(); await onChanged();
        }} onError={onError} />
      </section>
      <details className="verification"><summary>Verification</summary>
        <h2>Activity evidence</h2><pre>{JSON.stringify(steps, null, 2)}</pre>
        <Badge tone="hypothesis">Retrospective re-analysis</Badge>
        <p>Plan v{detail.plan.version} · {detail.plan.spec.comparison.treatment} vs {detail.plan.spec.comparison.control}</p>
        {proposal && <p className="hash">Next move v{proposal.version}: {proposal.sha256} · plan {detail.plan.sha256}</p>}
        {task && <p className="hash">Approval: {JSON.stringify(task.approval)} · updated {stamp(task.updated_at)}{task.title.startsWith("Demo example:") ? " · Seeded demo example with an example approval" : ""}</p>}
        <p>Edit freely; saving creates a new version and clears any approval bound to an older one. The historical records are never a contact list.</p>
        {run?.metrics && <section className="panel"><h2>Metric references</h2>
          <dl className="facts">{run.metrics.map(metric => <div key={metric.id}><dt>{metric.label}</dt><dd className="metric-id">{metric.id}{metric.exploratory ? " · exploratory" : ""}</dd></div>)}</dl>
        </section>}
        {run && <>      <section className="panel">
        <h2>Provenance of every number above</h2>
        <dl className="facts">
          <dt>Analysis artifact</dt>
          <dd className="hash">{run.artifact_id}</dd>
          <dt>Sandbox execution</dt>
          <dd className="hash">{run.execution_id}</dd>
          <dt>Program SHA-256</dt>
          <dd className="hash">{run.program_sha256}</dd>
          <dt>Analysis input SHA-256</dt>
          <dd className="hash">{run.input_sha256}</dd>
          <dt>Plan SHA-256</dt>
          <dd className="hash">{run.plan_sha256}</dd>
          <dt>Reconciliation</dt>
          <dd>
            {run.reconciliation?.status} · {run.reconciliation?.independent_implementation}
          </dd>
        </dl>
        <p className="muted">
          Repeated runs of the same plan, data and program produce the identical artifact; the run list under Scheduled
          work shows every attempt and its hash.
        </p>
      </section></>}
        {run && <ExploratoryBreakdowns run={run} />}
        <SourceTab detail={detail} /><TechnicalTab detail={detail} run={run} />
        <WorkTab detail={detail} onChange={async () => { await load(); await onChanged(); }} onError={onError} />
      </details>

    </>
  );
}

function ExploratoryBreakdowns({ run }: { run: Run }) {
  const exploratory = (run.metrics || []).filter(x => x.exploratory);
  return <>{exploratory.length > 0 && (
        <section className="panel">
          <h2>
            Exploratory breakdowns <Badge tone="hypothesis">descriptive, not confirmatory</Badge>
          </h2>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Breakdown</th>
                  <th>Purchase rate</th>
                  <th>Denominator</th>
                  <th>Metric id</th>
                </tr>
              </thead>
              <tbody>
                {exploratory.map((x) => (
                  <tr key={x.id}>
                    <td>{x.label}</td>
                    <td>{pct(x.value as number)}</td>
                    <td>
                      {num(x.denominator?.events ?? 0)} of {num(x.denominator?.n ?? 0)}
                    </td>
                    <td className="hash">{x.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            Pre-declared slices of the planned comparison with no intervals. Many slices invite chance findings; nothing
            here is presented as confirmed.
          </p>
        </section>
      )}</>;
}

function MetricCard({ metric, emphasis = false }: { metric: Metric; emphasis?: boolean }) {
  return (
    <div className={`metric ${emphasis ? "emphasis" : ""}`}>
      <span className="metric-label">{metric.label}</span>
      <strong>{formatMetric(metric)}</strong>
      <span className="metric-def">
        {metric.definition}
        {metric.interval_method ? ` · interval: ${metric.interval_method.replaceAll("_", " ")}` : ""}
      </span>
    </div>
  );
}

function RateChart({ title, metrics, caption }: { title: string; metrics: Metric[]; caption: string }) {
  const values = metrics.map((m) => ({
    label: m.label.replace(/^(Purchase|Visit) rate, /, ""),
    rate: (m.value as number) || 0,
    interval: m.interval,
    events: m.denominator?.events ?? 0,
    n: m.denominator?.n ?? 0,
  }));
  const top = Math.max(...values.map((v) => (v.interval ? v.interval[1] : v.rate)), 0.0001) * 1.15;
  const width = 420;
  const height = 190;
  const left = 56;
  const bottom = 150;
  const band = (width - left - 20) / values.length;
  const y = (rate: number) => bottom - (rate / top) * (bottom - 20);
  const ticks = [0, top / 2, top];
  return (
    <figure className="chart">
      <figcaption>
        <strong>{title}</strong>
      </figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}: ${values.map((v) => `${v.label} ${pct(v.rate)} (${v.events} of ${v.n})`).join("; ")}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={left} x2={width - 20} y1={y(t)} y2={y(t)} className="grid" />
            <text x={left - 6} y={y(t) + 4} textAnchor="end" className="axis">
              {pct(t, 1)}
            </text>
          </g>
        ))}
        {values.map((v, i) => {
          const x = left + band * i + band * 0.25;
          const w = band * 0.5;
          return (
            <g key={i}>
              <rect x={x} y={y(v.rate)} width={w} height={bottom - y(v.rate)} className={`bar bar-${i}`} />
              {v.interval && (
                <>
                  <line x1={x + w / 2} x2={x + w / 2} y1={y(v.interval[0])} y2={y(v.interval[1])} className="whisker" />
                  <line x1={x + w / 2 - 6} x2={x + w / 2 + 6} y1={y(v.interval[0])} y2={y(v.interval[0])} className="whisker" />
                  <line x1={x + w / 2 - 6} x2={x + w / 2 + 6} y1={y(v.interval[1])} y2={y(v.interval[1])} className="whisker" />
                </>
              )}
              <text x={x + w / 2} y={bottom + 16} textAnchor="middle" className="axis">
                {v.label}
              </text>
              <text x={x + w / 2} y={bottom + 30} textAnchor="middle" className="axis muted-text">
                {num(v.events)} of {num(v.n)}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="muted">{caption}</p>
    </figure>
  );
}

function DifferenceLine({ metric, unit }: { metric: Metric; unit: "pp" | "usd" }) {
  const value = metric.value as number | null;
  if (value === null || !metric.interval) return <p className="muted">Difference undefined (empty group).</p>;
  const [low, high] = metric.interval;
  const span = Math.max(Math.abs(low), Math.abs(high), Math.abs(value), 1e-9) * 1.2;
  const width = 420;
  const x = (v: number) => 20 + ((v + span) / (2 * span)) * (width - 40);
  const label = (v: number) => (unit === "pp" ? `${pp(v)} pp` : usd(v, true));
  return (
    <figure className="chart">
      <figcaption>
        <strong>{metric.label}</strong>
      </figcaption>
      <svg viewBox={`0 0 ${width} 70`} role="img" aria-label={`${metric.label}: ${formatMetric(metric)}`}>
        <line x1={20} x2={width - 20} y1={35} y2={35} className="grid" />
        <line x1={x(0)} x2={x(0)} y1={15} y2={55} className="zero" />
        <text x={x(0)} y={66} textAnchor="middle" className="axis">
          0
        </text>
        <line x1={x(low)} x2={x(high)} y1={35} y2={35} className="interval" />
        <circle cx={x(value)} cy={35} r={5} className="point" />
        <text x={x(low)} y={26} textAnchor="middle" className="axis">
          {label(low)}
        </text>
        <text x={x(high)} y={26} textAnchor="middle" className="axis">
          {label(high)}
        </text>
      </svg>
      <p className="muted">
        {formatMetric(metric)} · {metric.definition} · interval method {metric.interval_method?.replaceAll("_", " ")}.{" "}
        {low > 0 ? "The interval lies above zero." : high < 0 ? "The interval lies below zero." : "The interval includes zero: inconclusive, which is a usable result."}
      </p>
    </figure>
  );
}

function ResultsTab({ detail, run, working }: { detail: PlanDetail; run: Run | null; working: boolean }) {
  if (!run || run.status !== "succeeded" || !run.metrics) {
    return (
      <Empty
        title={working ? "The analysis is running on the server." : detail.runs.length ? "No successful result yet." : "Nothing has run yet."}
        text={
          working
            ? "Your Vultr worker is analysing the campaign. This page refreshes itself."
            : "Use \"Run analysis now\". The job is durable: it runs even if you close this tab."
        }
      />
    );
  }
  const m = byId(run.metrics);
  const artifact = run.artifact_id || "";
  
  const groups = (prefix: string) => [m[`treatment.${prefix}`], m[`control.${prefix}`]].filter(Boolean);
  return (
    <div className="stack">
      <section className="panel">
        <h2>
          Primary outcome: purchase conversion per assigned customer 
        </h2>
        <div className="two">
          <p className="muted">Purchases divided by all assigned customers in each original arm; whiskers are 95% Wilson score intervals.</p>
          <DifferenceLine metric={m["conversion.difference_pp"]} unit="pp" />
        </div>
        <div className="metric-grid">
          <MetricCard metric={m["treatment.conversion_rate"]} />
          <MetricCard metric={m["control.conversion_rate"]} />
          <MetricCard metric={m["conversion.difference_pp"]} emphasis />
          {m["conversion.relative_change"] && <MetricCard metric={m["conversion.relative_change"]} />}
        </div>
      </section>
      <section className="panel">
        <h2>Secondary outcomes: visits and spend per assigned customer</h2>
        <div className="two">
          <RateChart title="Visit rate by original arm" metrics={groups("visit_rate")} caption={`Visits divided by assigned customers; 95% Wilson intervals.`} />
          <DifferenceLine metric={m["spend.incremental_per_customer"]} unit="usd" />
        </div>
        <div className="metric-grid">
          <MetricCard metric={m["visit.difference_pp"]} />
          <MetricCard metric={m["treatment.spend_per_customer"]} />
          <MetricCard metric={m["control.spend_per_customer"]} />
          <MetricCard metric={m["spend.incremental_per_customer"]} emphasis />
          <MetricCard metric={m["treatment.spend_total"]} />
          <MetricCard metric={m["control.spend_total"]} />
        </div>
        <p className="muted">
          Measured historical spend and estimated incremental historical revenue per assigned customer. This is not
          SalesDesk revenue, not profit and not a projection; cost, margin and audience size are entered separately
          under Next move as labelled assumptions.
        </p>
      </section>

    </div>
  );
}

function InterpretationTab({ run, working }: { run: Run | null; working: boolean }) {
  const interpretation = run?.interpretation;
  if (!run || run.status !== "succeeded")
    return <Empty title={working ? "Waiting for the analysis." : "No result to interpret yet."} text="Your analyst reads the campaign result here." />;
  if (!interpretation || interpretation.status !== "succeeded" || !interpretation.rendered)
    return (
      <div className="stack">
        <section className="panel">
          <h2>
            Interpretation <Badge tone="failed">{interpretation ? "AI step failed" : "missing"}</Badge>
          </h2>
          <p>
            {interpretation?.label || "No interpretation was produced."}{" "}
            {interpretation?.failure_reason && <span className="code">{interpretation.failure_reason}</span>}
          </p>
          <p className="muted">
            The validated statistical result is unchanged and remains available under Results. Run the analysis again
            once the model budget or plan is available; nothing is substituted silently.
          </p>
        </section>
      </div>
    );
  const r = interpretation.rendered;
  return (
    <div className="stack">
      <section className="panel">
        <h2>
          Question answered <ProvenanceBadge provenance={interpretation.provenance} />
        </h2>
        <p>{r.question_answered}</p>
        
      </section>
      <section className="panel">
        <h2>Reading of the result</h2>
        <p>{r.interpretation}</p>
      </section>
      <div className="two">
        <section className="panel">
          <h2>Alternative explanations</h2>
          <ul className="plain">
            {r.alternative_explanations.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>
        <section className="panel">
          <h2>Unknowns</h2>
          <ul className="plain">
            {r.unknowns.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </section>
      </div>
      <details className="verification"><summary>Analysis context</summary><section className="panel">
        <h2>What this result does not establish</h2>
        <p className="muted">
          An original randomized result supports a historical arm comparison under the study assumptions. It does not
          establish effects of new e-mail copy, present-day audiences, individual customers, business-to-business
          follow-ups or future SalesDesk revenue. The proposed next step under Next move is a planning packet, not a
          launch.
        </p>
      </section></details>
    </div>
  );
}

function listToText(items: string[]) {
  return items.join("\n");
}
function textToList(text: string) {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

function NextActionTab({ detail, run, proposal, onChange, onError, onDirty }: { detail: PlanDetail; run: Run | null; proposal: Proposal | null; onChange: () => Promise<void>; onError: (m: string) => void; onDirty: (dirty: boolean) => void }) {
  const [editing, setEditing] = useState(false);
  const blank: ProposalContent = {
    hypothesis: "",
    variant_a: "",
    variant_b: "",
    audience_requirements: [],
    unit_of_randomization: "customer",
    primary_outcome: "",
    observation_window: "",
    decision_rule: "",
    missing_inputs: [],
    scenario_assumptions: { audience_size: null, gross_margin: null, campaign_cost_usd: null },
    sample_size_inputs: { minimum_detectable_pp: null, alpha: null, power: null },
    notes: "",
  };
  const [draft, setDraft] = useState<ProposalContent>(proposal?.content || blank);
  const [saving, setSaving] = useState(false);
  const requestId = useRef<string | null>(null);
  useEffect(() => {
    setDraft(proposal?.content || blank);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proposal?.sha256]);
  const ready = !!run && run.status === "succeeded";
  const dirty = JSON.stringify(draft) !== JSON.stringify(proposal?.content || blank);
  useEffect(() => { onDirty(dirty); }, [dirty, onDirty]);
  if (!ready) return <Empty title="Run the analysis first." text="A next move is proposed from a validated result." />;
  const set = (key: keyof ProposalContent, value: unknown) => { onDirty(true); setDraft((d) => ({ ...d, [key]: value })); };
  const scenario = draft.scenario_assumptions;
  const sample = draft.sample_size_inputs;
  const m = byId(run!.metrics);
  const incremental = m["spend.incremental_per_customer"];
  const projection = (() => {
    if (!incremental || incremental.value === null || !incremental.interval) return null;
    if (scenario.audience_size === null || scenario.gross_margin === null || scenario.campaign_cost_usd === null) return null;
    const cost = Number(scenario.campaign_cost_usd) * 100;
    if (!Number.isFinite(cost)) return null;
    const point = (incremental.value as number) * scenario.audience_size;
    const low = incremental.interval[0] * scenario.audience_size;
    const high = incremental.interval[1] * scenario.audience_size;
    const contribution = (v: number) => v * (scenario.gross_margin as number) - cost;
    return {
      revenue: [usd(low), usd(point), usd(high)],
      contribution: [usd(contribution(low)), usd(contribution(point)), usd(contribution(high))],
      roi: cost > 0 ? `${((contribution(point) / cost) * 100).toFixed(0)}% (projected, not realized)` : "undefined: campaign cost is zero",
    };
  })();
  async function save() {
    onError("");
    setSaving(true);
    requestId.current ||= newId();
    try {
      await post<Proposal>(`/api/experiments/plans/${detail.plan.id}/proposal`, {
        proposal: draft,
        base_version: proposal?.version || 0,
        request_id: requestId.current,
      });
      requestId.current = null;
      await onChange();
      setEditing(false);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  if (!editing) return <section className="panel next-move-summary">
    <div className="row-between"><h2>Next move</h2><button className="secondary" onClick={() => setEditing(true)}>Edit</button></div>
    <dl className="move-facts">{[
      ["Hypothesis", draft.hypothesis],
      ["Who", draft.audience_requirements.join(" · ")],
      ["Compare", `${draft.variant_a} / ${draft.variant_b}`],
      ["Measure", `${draft.primary_outcome} · ${draft.observation_window}`],
      ["Decision rule", draft.decision_rule],
    ].map(([label, value]) => <div key={label}><dt>{label}</dt><dd title={value}>{shortCopy(value, 15)}</dd></div>)}</dl>
  </section>;
  return (
    <div className="stack next-move-editor">
      <section className="panel">
        <div className="row-between"><h2>Edit next move</h2><button className="secondary" onClick={() => { setDraft(proposal?.content || blank); setEditing(false); }}>Cancel</button></div>
        <label htmlFor="p-hypothesis">Hypothesis</label>
        <textarea id="p-hypothesis" rows={2} value={draft.hypothesis} maxLength={600} onChange={(e) => set("hypothesis", e.target.value)} />
        <div className="two">
          <div>
            <label htmlFor="p-a">Variant A</label>
            <textarea id="p-a" rows={2} value={draft.variant_a} maxLength={400} onChange={(e) => set("variant_a", e.target.value)} />
          </div>
          <div>
            <label htmlFor="p-b">Variant B</label>
            <textarea id="p-b" rows={2} value={draft.variant_b} maxLength={400} onChange={(e) => set("variant_b", e.target.value)} />
          </div>
        </div>
        <label htmlFor="p-audience">Audience requirements (one per line)</label>
        <textarea id="p-audience" rows={4} value={listToText(draft.audience_requirements)} onChange={(e) => set("audience_requirements", textToList(e.target.value))} />
        <div className="two">
          <div>
            <label htmlFor="p-unit">Unit of randomization</label>
            <input id="p-unit" type="text" value={draft.unit_of_randomization} maxLength={100} onChange={(e) => set("unit_of_randomization", e.target.value)} />
          </div>
          <div>
            <label htmlFor="p-window">Observation window</label>
            <input id="p-window" type="text" value={draft.observation_window} maxLength={120} onChange={(e) => set("observation_window", e.target.value)} />
          </div>
        </div>
        <label htmlFor="p-outcome">Primary outcome</label>
        <input id="p-outcome" type="text" value={draft.primary_outcome} maxLength={200} onChange={(e) => set("primary_outcome", e.target.value)} />
        <label htmlFor="p-rule">Decision rule</label>
        <textarea id="p-rule" rows={2} value={draft.decision_rule} maxLength={600} onChange={(e) => set("decision_rule", e.target.value)} />
        <label htmlFor="p-missing">Missing inputs (one per line)</label>
        <textarea id="p-missing" rows={3} value={listToText(draft.missing_inputs)} onChange={(e) => set("missing_inputs", textToList(e.target.value))} />
        <label htmlFor="p-notes">Notes</label>
        <textarea id="p-notes" rows={2} value={draft.notes} maxLength={1500} onChange={(e) => set("notes", e.target.value)} />
      </section>
      <details className="disclosure advanced-inputs"><summary>Advanced</summary>
      <section className="panel assumptions">
        <h2>
          Scenario assumptions <Badge tone="synthetic">entered, not measured</Badge>
        </h2>
        <p className="muted">
          Campaign cost, gross margin and future audience size are not in the data. Leave them empty until you know
          them; a projection appears only when all three are present and is always labelled.
        </p>
        <div className="three">
          <div>
            <label htmlFor="a-size">Future audience size</label>
            <input id="a-size" type="text" inputMode="numeric" value={scenario.audience_size ?? ""} onChange={(e) => set("scenario_assumptions", { ...scenario, audience_size: e.target.value ? Number(e.target.value.replace(/\D/g, "")) || null : null })} />
          </div>
          <div>
            <label htmlFor="a-margin">Gross margin (0 to 1)</label>
            <input id="a-margin" type="text" inputMode="decimal" value={scenario.gross_margin ?? ""} onChange={(e) => set("scenario_assumptions", { ...scenario, gross_margin: e.target.value === "" ? null : Number(e.target.value) })} />
          </div>
          <div>
            <label htmlFor="a-cost">Campaign cost (USD)</label>
            <input id="a-cost" type="text" inputMode="decimal" value={scenario.campaign_cost_usd ?? ""} onChange={(e) => set("scenario_assumptions", { ...scenario, campaign_cost_usd: e.target.value === "" ? null : e.target.value })} />
          </div>
        </div>
        {projection ? (
          <div className="metric-grid">
            <div className="metric assumption">
              <span className="metric-label">Projected incremental revenue</span>
              <strong>{projection.revenue[1]}</strong>
              <span className="metric-def">
                interval {projection.revenue[0]} to {projection.revenue[2]} · incremental spend per customer × audience size
              </span>
            </div>
            <div className="metric assumption">
              <span className="metric-label">Projected contribution</span>
              <strong>{projection.contribution[1]}</strong>
              <span className="metric-def">
                interval {projection.contribution[0]} to {projection.contribution[2]} · revenue × margin − cost
              </span>
            </div>
            <div className="metric assumption">
              <span className="metric-label">Projected ROI</span>
              <strong>{projection.roi}</strong>
              <span className="metric-def">Assumes a current audience behaves like the 2008 benchmark population; not established.</span>
            </div>
          </div>
        ) : (
          <p className="muted">No scenario shown: enter all three assumptions to see a labelled projection.</p>
        )}
        <h3>Sample-size inputs (required for the packet's sample-size check)</h3>
        <div className="three">
          <div>
            <label htmlFor="s-mde">Minimum detectable effect (pp)</label>
            <input id="s-mde" type="text" inputMode="decimal" value={sample.minimum_detectable_pp ?? ""} onChange={(e) => set("sample_size_inputs", { ...sample, minimum_detectable_pp: e.target.value === "" ? null : Number(e.target.value) })} />
          </div>
          <div>
            <label htmlFor="s-alpha">Alpha</label>
            <input id="s-alpha" type="text" inputMode="decimal" value={sample.alpha ?? ""} onChange={(e) => set("sample_size_inputs", { ...sample, alpha: e.target.value === "" ? null : Number(e.target.value) })} />
          </div>
          <div>
            <label htmlFor="s-power">Power</label>
            <input id="s-power" type="text" inputMode="decimal" value={sample.power ?? ""} onChange={(e) => set("sample_size_inputs", { ...sample, power: e.target.value === "" ? null : Number(e.target.value) })} />
          </div>
        </div>
        <p className="hint">Conventional values exist, but none is substituted for you: the packet reports these as missing until entered.</p>
      </section></details>
      <div className="draft-actions">
        <button className="secondary" onClick={() => void save()} disabled={!dirty || saving}>{saving ? "Saving…" : "Save next move"}</button>
      </div>
    </div>
  );
}

function TaskPanel({ detail, proposal, dirty, onChange, onError }: { detail: PlanDetail; proposal: Proposal | null; dirty: boolean; onChange: () => Promise<void>; onError: (m: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [due, setDue] = useState("");
  const operation = useRef({ create: newId(), approve: newId(), schedule: newId() });
  const pendingTask = useRef<Task | null>(null);
  useEffect(() => {
    pendingTask.current = null;
    operation.current = { create: newId(), approve: newId(), schedule: newId() };
  }, [proposal?.sha256]);
  const current = detail.tasks.find(t => t.proposal_sha256 === proposal?.sha256 && t.status !== "cancelled");
  async function approve() {
    if (!proposal || dirty) return;
    setBusy(true); onError("");
    try {
      let task = current || pendingTask.current;
      if (!task) {
        task = await post<Task>(`/api/experiments/plans/${detail.plan.id}/tasks`, {
          title: "Review the next-move packet", assignee_label: "Sales manager",
          proposed_action: "Review the prepared packet and decide whether to proceed with a current consenting audience.",
          due_date: null, request_id: operation.current.create,
        });
        pendingTask.current = task;
      }
      if (task.status === "pending_review") task = await post<Task>(`/api/experiments/tasks/${task.id}/approve`, {
        proposal_sha256: proposal.sha256, request_id: operation.current.approve,
      });
      pendingTask.current = task;
      if (["approved", "failed"].includes(task.status)) await post(`/api/experiments/tasks/${task.id}/schedule`, {
        due_at: due ? new Date(due).toISOString() : "now", request_id: operation.current.schedule,
      });
      await onChange();
    } catch (e) { onError((e as Error).message); }
    finally { setBusy(false); }
  }
  const scheduled = current && ["scheduled", "running", "ready_for_review", "completed"].includes(current.status);
  return <div className="answer-action" aria-label="Approval and packet">
    {scheduled ? current.packet_artifact_id ? <>
      <span className="status-pill" role="status">Ready for review</span>
      <a className="primary button-link" href={`/api/experiments/artifacts/${current.packet_artifact_id}/packet.md`}>Download packet</a>
      <PacketSummary artifactId={current.packet_artifact_id} />
    </> : <span className="status-pill" role="status">Preparing on Vultr · you can close this tab</span> : <>
      <button className="primary" disabled={busy || dirty || !proposal} onClick={() => void approve()}>{busy ? "Scheduling…" : "Approve & schedule"}</button>
      <details className="schedule-options"><summary>Schedule options</summary>
        <label htmlFor="prepare-at">Prepare packet (leave empty to start now)</label>
        <input id="prepare-at" type="datetime-local" value={due} onChange={e => setDue(e.target.value)} disabled={busy} />
      </details>
      {dirty && <p className="hint">Save your edits before approving.</p>}
    </>}
    {current?.status === "failed" && <p role="alert">Preparation stopped. Review Verification before retrying.</p>}
  </div>;

}

function PacketSummary({ artifactId }: { artifactId: string }) {
  const [packet, setPacket] = useState<Packet | null>(null);
  useEffect(() => {
    let cancelled = false;
    api<{ content: Packet }>(`/api/experiments/artifacts/${artifactId}`)
      .then((a) => {
        if (!cancelled) setPacket(a.content);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [artifactId]);
  if (!packet) return null;
  const p = packet.packet;
  return (
    <div className="packet">
      <details><summary>Inputs to add before launch ({p.readiness_checks.filter(c => c.status === "missing").length})</summary>
      <ul className="plain">
        {p.readiness_checks.filter(c => c.status === "missing").map((c) => (
          <li key={c.input}>
            {c.label}: <strong>{c.status}</strong>
            {c.value !== null && c.value !== undefined ? ` = ${String(c.value)}` : ""}
            {c.note ? ` · ${c.note}` : ""}
          </li>
        ))}
      </ul>
      </details>
      <details className="verification"><summary>Readiness checks</summary>
      <ul className="plain">
        {p.readiness_checks.map((c) => (
          <li key={c.input}>
            {c.label}: <strong>{c.status}</strong>
            {c.value !== null && c.value !== undefined ? ` = ${String(c.value)}` : ""}
            {c.note ? ` · ${c.note}` : ""}
          </li>
        ))}
      </ul>
      </details>
      <details><summary>Packet context</summary><p>{p.status.replaceAll("_", " ")}: {p.what_this_is}</p><p className="muted">Not claimed: {p.not_claimed.join(" ")}</p></details>
    </div>
  );
}

function WorkTab({ detail, onChange, onError }: { detail: PlanDetail; onChange: () => Promise<void>; onError: (m: string) => void }) {
  async function cancel(id: string) {
    onError("");
    try {
      await post(`/api/experiments/jobs/${id}/cancel`, {});
      await onChange();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  return (
    <div className="stack">
      <section className="panel">
        <h2>Jobs for this plan</h2>
        {detail.jobs.length === 0 ? (
          <p className="muted">No jobs yet.</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Kind</th>
                  <th>Due (UTC)</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Outcome</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {detail.jobs.map((j) => (
                  <tr key={j.id}>
                    <td className="hash">{j.id.slice(0, 8)}</td>
                    <td>{j.kind.replaceAll("_", " ")}</td>
                    <td>{stamp(j.due_at)}</td>
                    <td>
                      <Badge tone={TONES[j.status] || "warn"}>{j.status}</Badge>
                      {j.failure_reason ? <span className="code"> {j.failure_reason}</span> : ""}
                    </td>
                    <td>
                      {j.attempts} / {j.max_attempts}
                    </td>
                    <td className="muted">
                      {j.outcome ? Object.entries(j.outcome).map(([k, v]) => `${k}: ${String(v).slice(0, 12)}`).join(" · ") : "—"}
                    </td>
                    <td>
                      {ACTIVE_JOB.includes(j.status) && (
                        <button className="link-button" onClick={() => void cancel(j.id)}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted">
          A due job is claimed under a lease by the server's scheduler and executed by a worker subprocess. A lost worker
          is requeued once, then failed; duplicate dispatch cannot create a second artifact.
        </p>
      </section>
      <section className="panel">
        <h2>Runs</h2>
        {detail.runs.length === 0 ? (
          <p className="muted">No runs yet.</p>
        ) : (
          <ul className="plain">
            {detail.runs.map((r) => (
              <li key={r.id}>
                <span className="hash">{r.id.slice(0, 8)}</span> · attempt {r.attempt} · <Badge tone={TONES[r.status] || "warn"}>{r.status}</Badge>{" "}
                {r.failure_reason && <span className="code">{r.failure_reason}</span>} · {stamp(r.created_at)}
                {r.artifact_id && (
                  <>
                    {" "}
                    · artifact <span className="hash">{r.artifact_id.slice(0, 8)}</span>
                  </>
                )}
                {r.interpretation && (
                  <>
                    {" "}
                    · <ProvenanceBadge provenance={r.interpretation.provenance} /> {r.interpretation.status}
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function SourceTab({ detail }: { detail: PlanDetail }) {
  const spec = detail.plan.spec;
  return (
    <div className="stack">
      <DatasetCard dataset={detail.dataset} />
      <section className="panel">
        <h2>Saved analysis plan v{detail.plan.version}</h2>
        <dl className="facts">
          <dt>Question</dt>
          <dd>{spec.question}</dd>
          <dt>Comparison</dt>
          <dd>
            {spec.comparison.treatment} versus {spec.comparison.control} (original arms; the third arm is excluded)
          </dd>
          <dt>Primary outcome</dt>
          <dd>{spec.primary_outcome} per assigned customer</dd>
          <dt>Secondary outcomes</dt>
          <dd>{spec.secondary_outcomes.join(", ")} per assigned customer (zero spend included)</dd>
          <dt>Intervals</dt>
          <dd>95% Wilson score per arm; Newcombe hybrid score for the difference; seeded customer-level percentile bootstrap for spend</dd>
          <dt>Bootstrap</dt>
          <dd>
            seed {spec.bootstrap.seed}, {num(spec.bootstrap.resamples)} resamples
          </dd>
          <dt>Exploratory breakdowns</dt>
          <dd>{spec.exploratory_breakdowns.join(", ") || "none"}</dd>
          <dt>Nature</dt>
          <dd>Retrospective re-analysis of a known benchmark; not preregistered; no new holdout; no novel discovery claimed.</dd>
          <dt>Plan SHA-256</dt>
          <dd className="hash">{detail.plan.sha256}</dd>
        </dl>
      </section>
    </div>
  );
}

function TechnicalTab({ detail, run }: { detail: PlanDetail; run: Run | null }) {
  const execution = run?.execution;
  const generation = run?.generation;
  return (
    <div className="stack">
      <section className="panel">
        <h2>Sandbox execution</h2>
        {execution && !execution.unavailable ? (
          <>
            <dl className="facts">
              <dt>Execution</dt>
              <dd className="hash">{execution.id}</dd>
              <dt>Status</dt>
              <dd>
                {execution.status}
                {execution.failure_reason ? ` (${execution.failure_reason})` : ""} · exit code {execution.exit_code ?? "unknown"}
              </dd>
              <dt>Cleanup</dt>
              <dd>{execution.cleanup.removed ? "Container removal verified" : `Unverified (${execution.cleanup.reason})`}</dd>
              <dt>Validation</dt>
              <dd>{execution.validated_artifacts[0]?.validation || "no accepted artifact"}</dd>
              <dt>Image</dt>
              <dd className="hash">{execution.image}</dd>
              <dt>Runtime</dt>
              <dd>{execution.runtime ? Object.entries(execution.runtime).map(([k, v]) => `${k} ${v}`).join(" · ") : "—"}</dd>
              <dt>Task time</dt>
              <dd>{execution.task_elapsed_seconds ?? "—"} s inside a {execution.limits.wall_seconds} s wall limit, {Math.round(execution.limits.memory_bytes / 1048576)} MiB, no network</dd>
            </dl>
            <details>
              <summary>Resource limits and task output</summary>
              <pre>{JSON.stringify(execution.limits, null, 2)}</pre>
              <pre>{execution.log || "No task output."}</pre>
            </details>
          </>
        ) : (
          <p className="muted">{execution?.unavailable ? `Execution record unavailable: ${execution.unavailable}` : "No execution yet."}</p>
        )}
      </section>
      <section className="panel">
        <h2>Reconciliation</h2>
        {run?.reconciliation ? (
          <ul className="plain">
            {run.reconciliation.checks.map((c, i) => (
              <li key={i}>{Object.entries(c).map(([k, v]) => `${k}: ${v}`).join(" · ")}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">No reconciliation yet.</p>
        )}
        <p className="muted">
          Program SHA-256 <span className="hash">{detail.program_sha256}</span>. Counts and currency sums are recomputed by the importer with
          Decimal arithmetic; Wilson and Newcombe intervals are recomputed by the controller; hashes bind data, plan and program.
        </p>
      </section>
      <section className="panel">
        <h2>Model requests</h2>
        {generation ? (
          <>
            <p>
              <ProvenanceBadge provenance={generation.mode || "deterministic"} /> {PROVENANCE[generation.mode || "deterministic"]?.detail}
            </p>
            {generation.model && (
              <p className="muted">
                Model {generation.model}
                {generation.budget ? ` · ${generation.budget.reserved_requests} of ${generation.budget.max_requests} approved requests reserved, $${generation.budget.reserved_usd} reserved` : ""}
                {generation.usage?.analysis ? ` · actual usage ${generation.usage.analysis.prompt_tokens} input / ${generation.usage.analysis.completion_tokens} completion tokens (logged separately from the reservation)` : ""}
              </p>
            )}
            {Object.keys(generation.receipts).length === 0 && <p className="muted">No model request was made for this run.</p>}
            {generation.diagnostics.map((d, i) => (
              <div className="diagnostic" key={i}>
                <pre>{JSON.stringify(d, null, 2)}</pre>
                <p className="muted">Sanitized: field path, stage and types only. Rejected content is never stored.</p>
              </div>
            ))}
          </>
        ) : (
          <p className="muted">No run yet.</p>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------- Queue
export function QueueView({ overview, onChange, onError }: { overview: Overview; onChange: () => Promise<void>; onError: (m: string) => void }) {
  const plans = Object.fromEntries(overview.plans.map((p) => [p.id, p]));
  async function cancel(id: string) {
    onError("");
    try {
      await post(`/api/experiments/jobs/${id}/cancel`, {});
      await onChange();
    } catch (e) {
      onError((e as Error).message);
    }
  }
  return (
    <>
      <div className="heading">
        <h1>Action queue</h1>
        <p className="lede">Tasks awaiting approval, scheduled preparation, work in progress and results ready for review, across every saved analysis in this session.</p>
      </div>
      <div className="stack">
        <section className="panel">
          <h2>Tasks</h2>
          {overview.tasks.length === 0 ? (
            <p className="muted">No tasks yet.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Task</th>
                    <th>Assignee</th>
                    <th>Due</th>
                    <th>Status</th>
                    <th>Analysis</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.tasks.map((t) => (
                    <tr key={t.id}>
                      <td>{t.title}</td>
                      <td>{t.assignee_label}</td>
                      <td>{t.due_date || "—"}</td>
                      <td>
                        <Badge tone={TONES[t.status] || "warn"}>{taskLabel(t.status)}</Badge>
                      </td>
                      <td>
                        <a href={`#/experiments/${t.plan_id}`}>{plans[t.plan_id]?.title || "Open analysis"}</a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <details className="verification"><summary>Verification</summary>
        <section className="panel">
          <h2>Jobs</h2>
          {overview.jobs.length === 0 ? (
            <p className="muted">No jobs yet.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Job</th>
                    <th>Kind</th>
                    <th>Due (UTC)</th>
                    <th>Status</th>
                    <th>Attempts</th>
                    <th>Last event</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {overview.jobs.map((j) => (
                    <tr key={j.id}>
                      <td className="hash">{j.id.slice(0, 8)}</td>
                      <td>{j.kind.replaceAll("_", " ")}</td>
                      <td>{stamp(j.due_at)}</td>
                      <td>
                        <Badge tone={TONES[j.status] || "warn"}>{j.status}</Badge>
                        {j.failure_reason ? <span className="code"> {j.failure_reason}</span> : ""}
                      </td>
                      <td>
                        {j.attempts} / {j.max_attempts}
                      </td>
                      <td className="muted">
                        {j.events[j.events.length - 1]?.stage} {time(j.events[j.events.length - 1]?.at)}
                      </td>
                      <td>
                        {ACTIVE_JOB.includes(j.status) && (
                          <button className="link-button" onClick={() => void cancel(j.id)}>
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
<section className="panel">
          <h2>Scheduler</h2>
          <p className="muted">
            Jobs run on the Vultr-hosted API process: due work is claimed under a {overview.scheduler.lease_seconds}-second lease and executed by a worker subprocess. {overview.scheduler.last_error ? `Last scheduler error: ${overview.scheduler.last_error}.` : "No scheduler error recorded."} Limits in this mode: {overview.limits.max_plans} plans, {overview.limits.max_runs} runs, {overview.limits.max_tasks} tasks, {overview.limits.max_scheduled} queued jobs per session.
          </p>
        </section></details>
      </div>
    </>
  );
}
