import { AnalystActivity, type ActivityStep } from "./activity";
import { useEffect, useRef, useState } from "react";
import { api, Badge, day, Empty, ERRORS, MODES, money, newId, post, time } from "./shared";

type Sample = { id: string; title: string; note: string; synthetic: boolean };
type Capability = { id: string; label: string; summary: string };
type Check = {
  workflow_id: string;
  status: string;
  failure_reason: string;
  usage: { prompt_tokens: number; completion_tokens: number };
};
export type Workspace = {
  seeded_demo?: boolean;
  experiments?: { generation_mode: string; limits: Record<string, number>; datasets: string[] };
  capability: Capability;
  default_offering: string;
  max_offering_chars: number;
  samples: Sample[];
  generation_mode: string;
  public_demo?: boolean;
  inference_checkpoint: {
    checks: Check[];
    reserved_usd: string;
    remaining_requests: number;
  } | null;
  extractor: { label: string; source_kind: string; script_sha256: string };
  script: string;
  limits: {
    max_session_prospects: number;
    max_total_prospects: number;
    max_pages_per_prospect: number;
  };
};
type Source = {
  id: string;
  requested_url: string;
  final_url: string | null;
  status: string;
  failure_reason: string | null;
  fetched_at: string | null;
  http_status: number | null;
  title: string | null;
  kind: string;
  text_chars: number;
  sha256: string | null;
};
type Claim = {
  id: string;
  text: string;
  text_kind?: string | null;
  verification?: string;
  source_id: string;
  excerpt: string;
  topic: string;
  strength: string | null;
};
type Brief = {
  provenance: string;
  company_name: string;
  company_summary: {
    text: string;
    text_kind?: string | null;
    source_id: string;
    excerpt: string;
  } | null;
  claims: Claim[];
  opportunity_hypothesis: { text: string; claim_ids: string[]; label: string };
  unknowns: string[];
  evidence_chars: number;
};
type Demo = {
  decision: string;
  reason: string;
  claim_ids: string[];
  capability: string;
  status: string;
  execution_id: string | null;
  failure_reason: string | null;
  result_text: string | null;
  input_label?: string;
  proves?: string;
  extractor?: { label: string; source_kind: string; script_sha256: string };
};
type Draft = {
  version: number;
  sha256: string;
  subject: string;
  body: string;
  provenance: string;
  created_at: string;
  citations:
    | {
        marker: number;
        claim_id: string;
        url: string | null;
        fetched_at: string | null;
        excerpt: string;
      }[]
    | null;
};
type Result = {
  document_id: string;
  supplier: string;
  date: string;
  currency: string;
  total_cents: number;
  items: { description: string; quantity: number; unit_cents: number }[];
};
type Execution = {
  id: string;
  status: string;
  failure_reason: string | null;
  exit_code: number | null;
  source_kind: string;
  cleanup: { removed: boolean; reason: string | null };
  validated_artifacts: { sha256: string; validation: string }[];
  limits: Record<string, number>;
  log: string | null;
  input: string | null;
  result: Result | null;
};
type Diagnostic = {
  contract: string;
  failure_reason: string;
  diagnostic: Record<string, unknown> | null;
  finish_reason: string | null;
  usage: Record<string, number> | null;
  http_status: number | null;
};
type Prospect = {
  id: string;
  created_at: string;
  finished_at: string | null;
  status: string;
  failure_reason: string | null;
  offering: { text: string };
  prospect: {
    kind: string;
    input_url: string | null;
    sample: string | null;
    display_name: string;
  };
  generation: {
    mode: string;
    model: string | null;
    receipts: Record<string, string>;
    diagnostics: Diagnostic[];
    budget?: Record<string, string | number>;
    usage?: Record<string, Record<string, number>>;
  };
  events: { stage: string; at: string }[];
  sources: Source[];
  brief: Brief | null;
  demo: Demo | null;
  draft: Draft | null;
  drafts_history: Draft[];
  review: { state: string; draft_sha256: string | null; reviewed_at: string | null };
  execution: Execution | null;
};

const ACTIVE = ["queued", "researching", "deciding", "demonstrating", "drafting"];
const SOURCE_FAILURES: Record<string, string> = {
  address_blocked: "Blocked: the host resolved to a private or reserved address.",
  ip_literal_rejected: "Blocked: redirect to an IP address.",
  redirect_limit_exceeded: "Stopped: too many redirects.",
  dns_resolution_failed: "Could not resolve the host.",
  fetch_timeout: "Timed out.",
  transport_error: "Connection failed.",
  response_too_large: "Page larger than the 512 KiB cap.",
  content_type_rejected: "Not an HTML or text page.",
  content_encoding_rejected: "Compressed response refused.",
  retrieval_deadline_exceeded: "Skipped: research deadline reached.",
};

const isActive = (p: Prospect | null) => !!p && ACTIVE.includes(p.status);

function statusLabel(p: Prospect) {
  if (p.status === "ready") return p.review.state === "reviewed" ? "Reviewed" : "Ready";
  if (p.status === "failed") return "Stopped";
  return "Running";
}

function Landing({
  workspace,
  busy,
  onStarted,
  onError,
}: {
  workspace: Workspace;
  busy: boolean;
  onStarted: (p: Prospect) => Promise<void>;
  onError: (message: string) => void;
}) {
  const [offering, setOffering] = useState(workspace.default_offering);
  const [url, setUrl] = useState("");
  const [sample, setSample] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const requestId = useRef<string | null>(null);
  const [showMore, setShowMore] = useState(false);
  const primary = workspace.samples[0];

  async function start(target: { url?: string; sample?: string }) {
    onError("");
    setStarting(true);
    requestId.current ||= newId();
    try {
      const record = await post<Prospect>("/api/prospects", {
        offering,
        prospect_url: target.url || null,
        sample: target.sample || null,
        request_id: requestId.current,
      });
      requestId.current = null;
      await onStarted(record);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setStarting(false);
    }
  }
  const disabled = busy || starting;
  const publicDemo = !!workspace.public_demo;
  return (
    <>
      <div className="heading">
        <h1>Research a prospect, prove one thing, draft the ask.</h1>
        <p className="lede">
          Give SalesDesk your offering and a prospect website. It reads a few public pages,
          separates facts from a hypothesis, decides whether its one supported demonstration
          is relevant, runs it in a disposable sandbox when it is, and prepares an editable
          draft you review before anything leaves your desk.
        </p>
        {publicDemo && (
          <p className="public-note" role="note">
            <Badge tone="synthetic">Public demo</Badge> This copy runs the labelled synthetic
            scenarios with a Vultr analyst. Records here are demonstration data; drafts stay unsent.
          </p>
        )}
      </div>
      <div className="landing-grid">
        <form
          className="panel compose"
          onSubmit={(e) => {
            e.preventDefault();
            void start({ url: url.trim() });
          }}
        >
          <label htmlFor="offering">Your offering</label>
          <textarea
            id="offering"
            value={offering}
            maxLength={workspace.max_offering_chars}
            rows={5}
            onChange={(e) => setOffering(e.target.value)}
            disabled={disabled}
          />
          <p className="hint">
            {offering.length} / {workspace.max_offering_chars} characters. The first demo is
            written for a technical seller offering document-workflow automation.
          </p>
          {!publicDemo && <>
          <label htmlFor="url">Prospect website</label>
          <input
            id="url"
            type="url"
            inputMode="url"
            placeholder={
              publicDemo ? "Not available in the public demo" : "https://www.example-prospect.com"
            }
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={disabled || publicDemo}
            autoComplete="off"
          />
          <p className="hint">
            {publicDemo
              ? "Real-website research is switched off in this public demo. Use a synthetic scenario below."
              : `Up to ${workspace.limits.max_pages_per_prospect} public pages are fetched over plain HTTP with private-network, redirect, size and type limits. No login, no browser automation.`}
          </p>
          </>}
          <div className="compose-actions">
            {!publicDemo && <button className="primary" type="submit" disabled={disabled || !url.trim()}>{starting ? "Starting…" : "Research this prospect"}</button>}
            {primary && (
              <button
                className={publicDemo ? "primary" : "secondary"}
                type="button"
                disabled={disabled}
                onClick={() => void start({ sample: primary.id })}
              >
                Use the sample scenario
              </button>
            )}
          </div>
          {primary && (
            <p className="sample-note">
              <Badge tone="synthetic">Synthetic</Badge> {primary.title}: {primary.note} The pages
              are invented and read from disk; no network request is made for them.
            </p>
          )}
          {workspace.samples.length > 1 && (
            <div className="more-samples">
              <button
                type="button"
                className="link-button"
                onClick={() => setShowMore((v) => !v)}
                aria-expanded={showMore}
              >
                {showMore ? "Hide other synthetic scenarios" : "Other synthetic scenarios"}
              </button>
              {showMore && (
                <ul>
                  {workspace.samples.slice(1).map((s) => (
                    <li key={s.id}>
                      <button
                        type="button"
                        className="link-button"
                        disabled={disabled}
                        onClick={() => {
                          setSample(s.id);
                          void start({ sample: s.id });
                        }}
                        aria-pressed={sample === s.id}
                      >
                        {s.title}
                      </button>{" "}
                      <span className="muted">{s.note}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {busy && <p className="hint">Another prospect is running. New work waits for it.</p>}
        </form>
        <details className="verification"><summary>Verification</summary><section className="panel scope" aria-labelledby="scope-heading">
          <h2 id="scope-heading">What SalesDesk can demonstrate</h2>
          <p>
            <strong>{workspace.capability.label}.</strong> {workspace.capability.summary}
          </p>
          <p>
            That is the only live demonstration SalesDesk runs. For any other offering it still
            researches the prospect and drafts an evidence-backed introduction, but it will not
            pretend to demonstrate the product.
          </p>
          <h3>What the controller checks</h3>
          <ul className="checks">
            <li>
              Every fact shown is a verbatim excerpt from a fetched page with its URL and capture
              time. Model restatements and the opportunity are labelled; they are not verified facts.
            </li>
            <li>The opportunity is labelled a hypothesis, next to what remains unknown.</li>
            <li>A failed retrieval is reported as a limitation, not as evidence about the prospect.</li>
            <li>
              The demonstration runs only on labelled synthetic documents, never on the prospect's
              files, and its output is compared with the expected answer as canonical JSON values.
            </li>
            <li>A failed demonstration is left out of the draft; a skipped one is explained.</li>
            <li>
              The draft contract refuses quantities, savings language and demonstration claims that
              the cited sources, your offering or a verified demonstration do not support. It checks
              wording against evidence, not truth: review every draft before sending.
            </li>
          </ul>
          <div className="mode-note">
            <Badge tone={workspace.generation_mode}>
              {MODES[workspace.generation_mode]?.label || workspace.generation_mode}
            </Badge>
            <span>{MODES[workspace.generation_mode]?.detail}</span>
          </div>
        </section></details>
      </div>
    </>
  );
}

function ProspectView({
  prospect,
  workspace,
  onChange,
  onError,
}: {
  prospect: Prospect;
  workspace: Workspace;
  onChange: (p: Prospect) => void;
  onError: (message: string) => void;
}) {
  const [tab, setTab] = useState<"research" | "demo" | "outreach" | "details">("research");
  const active = isActive(prospect);
  const mode = prospect.draft?.provenance || prospect.brief?.provenance || prospect.generation.mode;
  return (
    <>
      <div className="prospect-head">
        <div>
          <h1>{prospect.prospect.display_name}</h1>
          <p className="lede small">
            {prospect.prospect.kind === "synthetic_fixture" ? (
              <>
                <Badge tone="synthetic">Synthetic sample</Badge> Invented pages read from disk.
              </>
            ) : (
              <>
                Public pages from{" "}
                <a href={prospect.prospect.input_url!} rel="noreferrer noopener" target="_blank">
                  {prospect.prospect.input_url}
                </a>
              </>
            )}{" "}
            <Badge tone={mode}>{MODES[mode]?.label || mode}</Badge>
          </p>
        </div>
        <Badge tone={prospect.status === "failed" ? "failed" : prospect.status === "ready" ? "ok" : "running"}>
          {statusLabel(prospect)}
        </Badge>
      </div>
      <AnalystActivity steps={[
        ["researching", "Researching the prospect"], ["deciding", "Brief prepared"],
        ["demonstrating", "Demonstration decision"], ["drafting", "Drafting your next move"],
        ["ready", "Awaiting your approval"],
      ].map(([stage, label]): ActivityStep => {
        const event = prospect.events.find(e => e.stage === stage);
        const reached = !!event || (stage === "demonstrating" && !!prospect.demo);
        return { label, at: event?.at, state: prospect.status === stage && active ? "running" : reached ? "done" : "pending",
          evidence: stage === "researching" ? prospect.sources : stage === "demonstrating" ? prospect.demo : stage === "drafting" ? prospect.generation : undefined };
      })} />
      {prospect.status === "failed" && (
        <div className="alert" role="alert">
          <strong>This prospect stopped.</strong>{" "}
          {ERRORS[prospect.failure_reason || ""] || `Reason: ${prospect.failure_reason}.`} Saved
          progress is kept below; nothing was retried automatically.
          <span className="code"> {prospect.failure_reason}</span>
        </div>
      )}
      <div className="tabs" role="tablist" aria-label="Prospect views">
        {(
          [
            ["research", "Research"],
            ["demo", "Demonstration"],
            ["outreach", "Outreach"],
            ["details", "Verification"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            id={`tab-${id}`}
            role="tab"
            aria-selected={tab === id}
            aria-controls="tabpanel"
            className={id === "details" ? "tab-secondary" : ""}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
        {tab === "research" && <ResearchTab prospect={prospect} />}
        {tab === "demo" && <DemoTab prospect={prospect} />}
        {tab === "outreach" && (
          <OutreachTab prospect={prospect} onChange={onChange} onError={onError} />
        )}
        {tab === "details" && <DetailsTab prospect={prospect} workspace={workspace} />}
      </div>
    </>
  );
}

function sourceLabel(s: Source) {
  if (s.status === "fetched") return `Fetched ${time(s.fetched_at)}`;
  return SOURCE_FAILURES[s.failure_reason || ""] || `${s.status}: ${s.failure_reason}`;
}

function ResearchTab({ prospect }: { prospect: Prospect }) {
  const brief = prospect.brief;
  const sources = Object.fromEntries(prospect.sources.map((s) => [s.id, s]));
  if (!brief) {
    return (
      <Empty
        title={isActive(prospect) ? "Research in progress." : "No brief was produced."}
        text={
          isActive(prospect)
            ? "Pages are being fetched under the retrieval limits. Progress above comes from saved worker events."
            : "The job stopped before a brief could be written. The reason is shown above."
        }
      />
    );
  }
  const fetched = prospect.sources.filter((s) => s.status === "fetched").length;
  return (
    <div className="stack">
      <section className="panel">
        <h2>What {brief.company_name} demonstrably does</h2>
        {brief.company_summary ? (
          <>
            <blockquote>
              “{brief.company_summary.excerpt}”
              <footer>
                <SourceRef source={sources[brief.company_summary.source_id]} />
              </footer>
            </blockquote>
            {brief.company_summary.text_kind === "model_summary" && (
              <p className="muted restatement">
                <Badge tone="hypothesis">Model summary</Badge> {brief.company_summary.text}{" "}
                <span>(not a verified fact; the quotation above is the evidence)</span>
              </p>
            )}
          </>
        ) : (
          <p className="muted">No descriptive text was retrieved.</p>
        )}
        <p className="muted">
          {fetched} of {prospect.sources.length} requested page{prospect.sources.length === 1 ? "" : "s"}{" "}
          retrieved, {brief.evidence_chars.toLocaleString()} characters of text.{" "}
          <Badge tone={brief.provenance}>{MODES[brief.provenance]?.label || brief.provenance}</Badge>
        </p>
      </section>
      <section className="panel">
        <h2>Relevant facts</h2>
        {brief.claims.length ? (
          <table className="claims">
            <thead>
              <tr>
                <th>Fact (verbatim)</th>
                <th>Relevance</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {brief.claims.map((c) => (
                <tr key={c.id}>
                  <td>
                    <span className="claim-id">{c.id}</span> “{c.excerpt}”
                    {c.text_kind === "grounded_restatement" && c.text !== c.excerpt && (
                      <div className="muted restatement">
                        <Badge tone="hypothesis">Model restatement</Badge> {c.text}{" "}
                        <span>(built only from the quotation's words; not a separately verified fact)</span>
                      </div>
                    )}
                  </td>
                  <td>
                    {c.topic === "document_workflow"
                      ? c.strength === "strong"
                        ? "Documents handled manually"
                        : "Mentions documents"
                      : c.topic === "operations"
                        ? "Operations context"
                        : "Context"}
                  </td>
                  <td>
                    <SourceRef source={sources[c.source_id]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">
            No sentence on the fetched pages relates to document handling or operations. That is
            a finding about the pages, not a verdict on the company.
          </p>
        )}
      </section>
      <div className="two">
        <section className="panel hypothesis">
          <h2>
            Proposed opportunity <Badge tone="hypothesis">Hypothesis</Badge>
          </h2>
          <p>{brief.opportunity_hypothesis.text}</p>
          {brief.opportunity_hypothesis.claim_ids.length > 0 && (
            <p className="muted">Based on {brief.opportunity_hypothesis.claim_ids.join(", ")}.</p>
          )}
        </section>
        <details className="verification"><summary>Verification</summary><section className="panel">
          <h2>Unknowns and missing evidence</h2>
          <ul className="plain">
            {brief.unknowns.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </section></details>
      </div>
      <details className="verification"><summary>Verification</summary><section className="panel">
        <h2>Sources</h2>
        <ul className="sources">
          {prospect.sources.map((s) => (
            <li key={s.id}>
              <span className="claim-id">{s.id}</span>
              <span className="source-url">{s.final_url || s.requested_url}</span>
              <Badge tone={s.status === "fetched" ? "ok" : s.status === "blocked" ? "failed" : "warn"}>
                {s.status}
              </Badge>
              <span className="muted">
                {sourceLabel(s)}
                {s.status === "fetched" && s.title ? ` · ${s.title}` : ""}
                {s.kind === "synthetic_fixture" ? " · synthetic fixture" : ""}
              </span>
            </li>
          ))}
        </ul>
      </section></details>
    </div>
  );
}

function SourceRef({ source }: { source?: Source }) {
  if (!source) return <span className="muted">unknown source</span>;
  const href = source.final_url || source.requested_url;
  const external = href.startsWith("http");
  return (
    <span className="source-ref">
      {external ? (
        <a href={href} target="_blank" rel="noreferrer noopener">
          {source.id}
        </a>
      ) : (
        <span>{source.id}</span>
      )}
      <span className="muted"> captured {day(source.fetched_at)}</span>
    </span>
  );
}

function DemoTab({ prospect }: { prospect: Prospect }) {
  const demo = prospect.demo;
  const execution = prospect.execution;
  if (!demo) {
    return (
      <Empty
        title="No decision yet."
        text="The demonstration decision follows the prospect brief."
      />
    );
  }
  const result = execution?.result;
  return (
    <div className="stack">
      <section className="panel">
        <h2>
          Decision{" "}
          <Badge tone={demo.decision === "run" ? "ok" : "warn"}>
            {demo.decision === "run"
              ? "Run the demonstration"
              : demo.decision === "skip_irrelevant"
                ? "Skipped: not relevant"
                : "Skipped: insufficient evidence"}
          </Badge>
        </h2>
        <p>{demo.reason}</p>
        {demo.claim_ids.length > 0 && (
          <p className="muted">Cited facts: {demo.claim_ids.join(", ")}.</p>
        )}
      </section>
      {demo.decision === "run" && (
        <>
          <section className="panel">
            <h2>
              Result{" "}
              <Badge tone={demo.status === "verified" ? "ok" : demo.status === "failed" ? "failed" : "running"}>
                {demo.status === "verified"
                  ? "Verified"
                  : demo.status === "failed"
                    ? "Failed"
                    : "Running"}
              </Badge>
            </h2>
            <p className="input-label">
              <Badge tone="synthetic">Synthetic input</Badge> {demo.input_label}
            </p>
            {demo.status === "verified" && demo.result_text && <p>{demo.result_text}</p>}
            {demo.status === "failed" && (
              <p>
                The run did not pass verification ({demo.failure_reason}). The draft does not
                describe it as a success.
              </p>
            )}
            {result && (
              <>
                <div className="result-summary">
                  <div>
                    <span>Document</span>
                    <strong>{result.document_id}</strong>
                  </div>
                  <div>
                    <span>Supplier</span>
                    <strong>{result.supplier}</strong>
                  </div>
                  <div>
                    <span>Date</span>
                    <strong>{result.date}</strong>
                  </div>
                  <div className="total">
                    <span>Verified total</span>
                    <strong>{money(result.total_cents, result.currency)}</strong>
                  </div>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Description</th>
                        <th>Quantity</th>
                        <th>Unit price</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.items.map((item, i) => (
                        <tr key={i}>
                          <td>{item.description}</td>
                          <td>{item.quantity}</td>
                          <td>{money(item.unit_cents, result.currency)}</td>
                          <td>{money(item.quantity * item.unit_cents, result.currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
          <section className="panel">
            <h2>What this proves</h2>
            <p>{demo.proves}</p>
            {execution && (
              <dl className="facts">
                <dt>Extractor</dt>
                <dd>
                  {demo.extractor?.label}{" "}
                  <Badge tone="synthetic">{demo.extractor?.source_kind.replaceAll("_", " ")}</Badge>
                </dd>
                <dt>Execution</dt>
                <dd>{execution.id}</dd>
                <dt>Task exit code</dt>
                <dd>{execution.exit_code ?? "Unknown"}</dd>
                <dt>Sandbox removed</dt>
                <dd>{execution.cleanup.removed ? "Verified" : "Unverified"}</dd>
                <dt>Artifact validation</dt>
                <dd>{execution.validated_artifacts[0]?.validation || "No accepted artifact"}</dd>
                <dt>Result SHA-256</dt>
                <dd>{execution.validated_artifacts[0]?.sha256 || "none"}</dd>
              </dl>
            )}
            {execution?.input && (
              <details>
                <summary>Synthetic input document</summary>
                <pre>{execution.input}</pre>
              </details>
            )}
          </section>
        </>
      )}
      {demo.decision !== "run" && (
        <section className="panel">
          <h2>What the draft does instead</h2>
          <p>
            {demo.decision === "skip_irrelevant"
              ? "The draft stays research-only: it quotes what the site says, gives one sentence of context about the offering, and asks an open question. It does not pitch document extraction."
              : "The draft says plainly that little public information was found and asks before assuming anything. A retrieval problem is never presented as a fact about the prospect."}
          </p>
        </section>
      )}
    </div>
  );
}

function OutreachTab({
  prospect,
  onChange,
  onError,
}: {
  prospect: Prospect;
  onChange: (p: Prospect) => void;
  onError: (message: string) => void;
}) {
  const draft = prospect.draft;
  const [subject, setSubject] = useState(draft?.subject || "");
  const [body, setBody] = useState(draft?.body || "");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const requestId = useRef<string | null>(null);
  useEffect(() => {
    setSubject(draft?.subject || "");
    setBody(draft?.body || "");
  }, [draft?.sha256, draft?.subject, draft?.body]);
  if (!draft) {
    return (
      <Empty
        title={isActive(prospect) ? "The draft follows research and the decision." : "No draft was produced."}
        text={
          isActive(prospect)
            ? "It will appear here for review. Nothing is sent."
            : "The job stopped before drafting. Research that was saved is still available."
        }
      />
    );
  }
  const dirty = subject !== draft.subject || body !== draft.body;
  const reviewed = prospect.review.state === "reviewed" && prospect.review.draft_sha256 === draft.sha256;
  async function save() {
    onError("");
    setSaving(true);
    requestId.current ||= newId();
    try {
      const next = await post<Prospect>(`/api/prospects/${prospect.id}/draft`, {
        subject,
        body,
        base_sha256: draft!.sha256,
        request_id: requestId.current,
      });
      requestId.current = null;
      onChange(next);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  async function review() {
    onError("");
    try {
      onChange(
        await post<Prospect>(`/api/prospects/${prospect.id}/review`, {
          draft_sha256: draft!.sha256,
        }),
      );
    } catch (e) {
      onError((e as Error).message);
    }
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      onError("Clipboard access was refused by the browser. Select the text to copy it.");
    }
  }
  function download() {
    const blob = new Blob([`Subject: ${subject}\n\n${body}`], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `salesdesk-draft-${prospect.prospect.display_name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-v${draft!.version}.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
  }
  return (
    <div className="stack">
      <section className="panel draft">
        <div className="draft-head">
          <h2>
            Draft v{draft.version}{" "}
            <Badge tone={draft.provenance}>{MODES[draft.provenance]?.label || draft.provenance}</Badge>{" "}
            {reviewed ? (
              <Badge tone="ok">Reviewed · v{draft.version}</Badge>
            ) : (
              <Badge tone="warn">Not reviewed</Badge>
            )}
          </h2>
          <span className="muted hash">version {draft.sha256.slice(0, 12)}</span>
        </div>
        <label htmlFor="subject">Subject</label>
        <input id="subject" value={subject} maxLength={160} onChange={(e) => setSubject(e.target.value)} />
        <label htmlFor="body">Body</label>
        <textarea id="body" value={body} rows={18} maxLength={6000} onChange={(e) => setBody(e.target.value)} />
        <div className="draft-actions">
          <button className="primary" onClick={() => void save()} disabled={!dirty || saving}>
            {saving ? "Saving…" : "Save edits as new version"}
          </button>
          <button className="secondary" onClick={() => void review()} disabled={dirty || reviewed}>
            {reviewed ? "Reviewed" : "Mark this version reviewed"}
          </button>
          <button className="secondary" onClick={() => void copy()} disabled={dirty}>
            {copied ? "Copied" : "Copy draft"}
          </button>
          <button className="secondary" onClick={download} disabled={dirty}>
            Download .txt
          </button>
        </div>
        <p className="hint">
          {dirty
            ? "Unsaved edits. Saving creates a new version and clears any review."
            : reviewed
              ? `Reviewed ${time(prospect.review.reviewed_at)} for exactly this version. Editing invalidates it.`
              : "Review binds to this exact version. Nothing is sent by SalesDesk."}
        </p>
      </section>
      <section className="panel">
        <h2>Evidence used in this draft</h2>
        {draft.citations && draft.citations.length ? (
          <ol className="citations">
            {draft.citations.map((c) => (
              <li key={c.marker}>
                <span className="claim-id">[{c.marker}]</span> “{c.excerpt}”{" "}
                <span className="muted">
                  {c.url} · captured {day(c.fetched_at)}
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted">
            This draft cites no page facts, so it makes no claims about the prospect.
          </p>
        )}
        {prospect.demo?.decision === "run" && (
          <p className="muted">
            Demonstration: {prospect.demo.status === "verified"
              ? "verified and described as a synthetic sample run."
              : "failed verification and is left out of the draft."}
          </p>
        )}
      </section>
      {prospect.drafts_history.length > 0 && (
        <section className="panel">
          <h2>Previous versions</h2>
          <ul className="plain">
            {prospect.drafts_history.map((d) => (
              <li key={d.sha256}>
                v{d.version} · {MODES[d.provenance]?.label || d.provenance} · {time(d.created_at)} ·{" "}
                <span className="hash">{d.sha256.slice(0, 12)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function DetailsTab({ prospect, workspace }: { prospect: Prospect; workspace: Workspace }) {
  const execution = prospect.execution;
  const gen = prospect.generation;
  return (
    <div className="stack">
      <section className="panel">
        <h2>Saved progress</h2>
        <ul className="plain">
          {prospect.events.map((e, i) => (
            <li key={i}>
              <span className="claim-id">{e.stage}</span> {time(e.at)}
            </li>
          ))}
        </ul>
        <p className="muted">
          Prospect {prospect.id} · created {day(prospect.created_at)} {time(prospect.created_at)}
        </p>
      </section>
      <section className="panel">
        <h2>Model requests</h2>
        <p>
          <Badge tone={gen.mode}>{MODES[gen.mode]?.label || gen.mode}</Badge> {MODES[gen.mode]?.detail}
        </p>
        {gen.model && (
          <p className="muted">
            Model {gen.model}
            {gen.budget
              ? ` · ${gen.budget.reserved_requests} of ${gen.budget.max_requests} approved requests reserved, $${gen.budget.reserved_usd} reserved`
              : ""}
          </p>
        )}
        {Object.keys(gen.receipts).length === 0 && (
          <p className="muted">No model request was made for this prospect.</p>
        )}
        {gen.diagnostics.map((d, i) => (
          <div className="diagnostic" key={i}>
            <strong>{d.contract}</strong> <span className="code">{d.failure_reason}</span>
            <pre>{JSON.stringify({ ...d.diagnostic, finish_reason: d.finish_reason, usage: d.usage, http_status: d.http_status }, null, 2)}</pre>
            <p className="muted">
              Sanitized: field path, stage and types only. Rejected content is never stored or executed.
            </p>
          </div>
        ))}
      </section>
      {execution && (
        <section className="panel">
          <h2>Sandbox evidence</h2>
          <dl className="facts">
            <dt>Execution</dt>
            <dd>{execution.id}</dd>
            <dt>Status</dt>
            <dd>
              {execution.status}
              {execution.failure_reason ? ` (${execution.failure_reason})` : ""}
            </dd>
            <dt>Source kind</dt>
            <dd>{execution.source_kind}</dd>
            <dt>Cleanup</dt>
            <dd>{execution.cleanup.removed ? "Removed, verified" : `Unverified (${execution.cleanup.reason})`}</dd>
          </dl>
          <details>
            <summary>Resource limits and task output</summary>
            <pre>{JSON.stringify(execution.limits, null, 2)}</pre>
            <pre>{execution.log || "No task output."}</pre>
          </details>
          <details>
            <summary>
              Extractor source · {workspace.extractor.label} · SHA-256 {workspace.extractor.script_sha256.slice(0, 16)}…
            </summary>
            <pre>{workspace.script}</pre>
          </details>
        </section>
      )}
      <section className="panel">
        <h2>Live inference history</h2>
        {workspace.inference_checkpoint ? (
          <>
            {workspace.inference_checkpoint.checks.map((c, i) => (
              <p key={c.workflow_id} className="muted">
                Code-generation request {i + 1}: <span className="code">{c.failure_reason}</span> ·{" "}
                {c.usage.prompt_tokens.toLocaleString()} input / {c.usage.completion_tokens.toLocaleString()} completion tokens · workflow {c.workflow_id.slice(0, 8)}
              </p>
            ))}
            <p className="muted">
              {workspace.inference_checkpoint.remaining_requests} approved requests remain on that
              plan · ${workspace.inference_checkpoint.reserved_usd} reserved. These are historical
              CLI checks, separate from this prospect.
            </p>
          </>
        ) : (
          <p className="muted">No live inference evidence is installed in this workspace.</p>
        )}
      </section>
    </div>
  );
}


export function ProspectsWorkspace({ workspace }: { workspace: Workspace }) {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [current, setCurrent] = useState<Prospect | null>(null);
  const [composing, setComposing] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [polling, setPolling] = useState(true);

  async function loadProspects() {
    const records = await api<Prospect[]>("/api/prospects");
    records.sort((a, b) => b.created_at.localeCompare(a.created_at));
    setProspects(records);
    return records;
  }
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const records = await loadProspects();
        if (!cancelled && records[0]) {
          setCurrent(records[0]);
          setComposing(false);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (!isActive(current) || !polling) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const next = await api<Prospect>(`/api/prospects/${current!.id}`);
        if (!cancelled) {
          setCurrent(next);
          if (!isActive(next)) await loadProspects();
        }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message);
          setPolling(false);
        }
      }
    }, 700);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [current, polling]);

  function open(p: Prospect) {
    setCurrent(p);
    setComposing(false);
    setError("");
    setPolling(true);
  }
  const busy = prospects.some(isActive);
  return (
    <div className="prospects-layout">
      <aside className="prospects-list panel" aria-label="Your prospects">
        <button
          className="secondary wide"
          onClick={() => {
            setComposing(true);
            setError("");
          }}
          disabled={busy}
          aria-pressed={composing}
        >
          New prospect
        </button>
        <div className="side-label dark">Prospects</div>
        {prospects.length === 0 && <p className="muted">No prospects yet in this session.</p>}
        {prospects.map((p) => (
          <button
            key={p.id}
            className={`list-item ${!composing && current?.id === p.id ? "current" : ""}`}
            onClick={() => open(p)}
          >
            <span className={`dot ${p.status}`} aria-hidden="true" />
            <span className="side-name">{p.prospect.display_name}</span>
            <span className="side-status">{statusLabel(p)}</span>
          </button>
        ))}
        <p className="muted small-note">
          Research your first customers and prepare an unsent introduction for review.
        </p>
      </aside>
      <div className="prospects-main">
        {error && (
          <div className="alert" role="alert">
            {error}{" "}
            {!polling && (
              <button
                className="link-button"
                onClick={() => {
                  setPolling(true);
                  setError("");
                }}
              >
                Resume progress
              </button>
            )}
          </div>
        )}
        {loading ? (
          <p className="loading" role="status">
            Opening your prospects…
          </p>
        ) : composing || !current ? (
          <Landing
            workspace={workspace}
            busy={busy}
            onStarted={async (p) => {
              setCurrent(p);
              setComposing(false);
              setPolling(true);
              await loadProspects();
            }}
            onError={setError}
          />
        ) : (
          <ProspectView
            key={current.id}
            prospect={current}
            workspace={workspace}
            onChange={(p) => {
              setCurrent(p);
              setProspects((all) => all.map((x) => (x.id === p.id ? p : x)));
            }}
            onError={setError}
          />
        )}
      </div>
    </div>
  );
}
