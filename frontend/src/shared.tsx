import type { ReactNode } from "react";

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { "X-ProofDesk-Request": "1", ...options?.headers },
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(ERRORS[data.detail] || data.detail || "The request could not be completed.");
  return data as T;
}
export const post = <T,>(path: string, body: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
export const time = (value: string | null | undefined) =>
  value
    ? new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : "";
export const day = (value: string | null | undefined) => (value ? value.slice(0, 10) : "");
export const stamp = (value: string | null | undefined) => (value ? `${day(value)} ${time(value)}` : "");
export const money = (cents: number, currency: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(cents / 100);
// Display only: keep stored evidence and version-bound draft bytes intact.
export const displayCurrency = (text: string) => text.replace(
  /\b(\d+) cents \(([A-Z]{3}) (\d+\.\d{2})\)/g,
  (original, cents: string, currency: string, amount: string) => {
    if (!Number.isSafeInteger(Number(cents)) || Number(cents) !== Math.round(Number(amount) * 100)) return original;
    try { return money(Number(cents), currency); } catch { return original; }
  },
);
export const newId = () => crypto.randomUUID().replaceAll("-", "");

export function Badge({ tone, children }: { tone: string; children: ReactNode }) {
  return <span className={`badge ${tone}`} title={tone === "saved_replay" ? "cached response: previously accepted for identical inputs; no new request was made." : undefined}>{children}</span>;
}

export function Empty({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

export const MODES: Record<string, { label: string; detail: string }> = {
  deterministic: {
    label: "Analyst: Rule-based",
    detail:
      "Claims are verbatim sentences from fetched pages and the draft is a controller template. No model request was made.",
  },
  live_model: {
    label: "Analyst: Qwen 3.8 on Vultr Inference",
    detail:
      "The brief and draft were proposed by the Vultr model under an owner-approved budget. Quotations were checked against the fetched pages; restatements, the hypothesis and the draft were checked for unsupported quantities and claims, not for truth.",
  },
  saved_replay: {
    label: "Analyst: Qwen 3.8 on Vultr Inference",
    detail:
      "cached response: a previously accepted live model response for identical inputs. No new request was made.",
  },
  human_edited: { label: "Edited by you", detail: "You changed this version." },
};
export const ERRORS: Record<string, string> = {
  another_prospect_is_active:
    "Another prospect is still running. Wait for it to finish, then try again.",
  prospect_quota_reached:
    "This preview has reached its prospect allowance. Saved prospects remain available.",
  workspace_session_required: "Your workspace session expired. Reload the page to continue.",
  worker_abandoned: "The worker stopped before finishing. Nothing was retried automatically.",
  offering_length_rejected: "Describe your offering in 20 to 1,500 characters.",
  url_scheme_rejected: "Use a public http or https website address.",
  url_host_rejected: "That host is not allowed. Use a public company website.",
  ip_literal_rejected: "Enter a hostname, not an IP address.",
  url_port_rejected: "Custom ports are not allowed.",
  url_length_rejected: "That address is too long.",
  prospect_target_required: "Enter a prospect website or choose a sample scenario.",
  public_demo_samples_only:
    "This public demo researches only the labelled synthetic scenarios. Real websites and live model requests run in the private deployment.",
  draft_version_conflict:
    "The draft changed since you loaded it. Reload to see the current version.",
  draft_not_ready: "The draft is not ready yet.",
  live_plan_not_configured:
    "Analyst: Live mode was requested but no owner-approved plan is configured. No request was sent.",
  model_budget_exhausted: "The approved model budget is exhausted. No request was sent.",
  missing_vultr_credentials: "No inference credential is configured. No request was sent.",
  sandbox_busy: "The sandbox was busy with another task. Nothing was retried automatically.",
  cleanup_unverified: "Sandbox cleanup could not be verified, so the result was rejected.",
  research_contract_rejected:
    "The model's research response failed validation against the fetched pages. The sanitized diagnostic is under Verification; no draft was produced.",
  outreach_contract_rejected:
    "The model's draft failed validation (unsupported quantity, savings claim, citation or demonstration mention). See Verification.",
  analysis_contract_rejected:
    "The model's interpretation failed validation (unknown metric, raw number, ROI wording or an action against the historical records). The statistical result is unchanged.",
  provider_incomplete_response:
    "The model stopped before finishing its answer (completion cap). Nothing was executed.",
  provider_malformed_response:
    "The model response did not match the documented protocol. The sanitized diagnostic names the field.",
  provider_http_error: "The inference service returned an error status. No retry was made.",
  provider_deadline_exceeded: "The inference request exceeded its deadline. No retry was made.",
  experiment_quota_reached:
    "This workspace has reached its allowance for plans, runs or tasks. Saved work remains available.",
  experiment_queue_full: "Too much work is already queued for this session. Wait for it to finish.",
  proposal_version_conflict:
    "The proposal changed since you loaded it. Reload to see the current version.",
  approval_stale: "The approval no longer matches the current next move or analysis. Approve again.",
  task_not_approved: "Approve the task before scheduling preparation.",
  packet_not_ready: "The packet has not been prepared yet.",
  analysis_not_available: "Run the analysis successfully before creating a task.",
  proposal_required: "No proposed next move exists yet. Save one first.",
  due_at_out_of_range: "Choose a due time between now and the allowed horizon.",
  invalid_due_at: "Enter the due time as an ISO-8601 timestamp with a timezone.",
  invalid_plan_comparison: "Choose two different original campaign arms.",
  dataset_not_found: "That dataset is not imported in this workspace.",
  experiment_not_found: "That record does not exist in this session.",
};
