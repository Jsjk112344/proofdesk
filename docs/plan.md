# SalesDesk: plan to a credible Future of Work entry

This is the single forward plan. [STATUS.md](../STATUS.md) records observed results;
this file records scope, dependencies and acceptance criteria, never build estimates.
The owner approved this revision and the SalesDesk product name on 2026-11-05.

## Product and boundaries

SalesDesk helps a technical seller turn an offering and prospect website into sourced
research, a plausible opportunity, an optional working demonstration and an editable
outreach draft for human review. The first supported offering is document-workflow
automation. Extraction is a tool within the sales journey, not the product identity.

Selected challenge: **Powering the Future of Work**. Vultr hosts the central backend
and web app. Vultr inference and sandboxing are our implementation choices, not extra
requirements of this track. Existing Vultr names, system user/service, install paths,
environment keys and persisted identifiers remain compatible with `proofdesk`.

- Lead with the salesperson's outcome; keep technical evidence available as detail.
- Distinguish live model output, saved replay, synthetic inputs and deterministic execution.
- Quote presence does not establish that an attached claim is true or supported in context.
- No sending, new resources or public activation without the applicable authorization.
- Preserve historical records and exhausted ledgers; new plans never refund earlier use.
- Public figures need sanitized, accessible evidence. Ignored local files alone are not
  reviewer-accessible evidence. Publish only explicitly reviewed exports.

## Baseline: implemented, with limitations

The private Vultr app has a prospect workspace, bounded retrieval, rule-based research
and drafting, a demonstration decision, Docker execution and version-bound review.
Model contracts exist and have offline tests. No successful live sales-model workflow
has been observed. Original live-generation attempts failed before code execution.

The 2026-11-05 review reproduced two contract gaps offline:

- A fabricated lunar-warehouse claim passed when paired with a genuine freight excerpt.
- An unsupported statement about 42 warehouses passed the outreach contract.

`backend/app/sales/contracts.py` checks excerpt membership and selected textual patterns;
it does not establish arbitrary claim entailment. `execution/artifacts.py` compares
canonical serialized JSON values, not original output bytes. These findings supersede
the prior plan's proposed universal factuality and byte-exact guarantees. They do not
invalidate the separately observed sandbox and persistence checks.

## Phase 1: correct guarantees and protect the sales output

Needs: ordinary implementation and offline tests; no paid inference required.

1. Reproduce both gaps as regression cases before changing contracts. Add supported
   positive counterparts, including numbers attributed to the correct subject and unit.
2. Separate verified source quotations from model interpretations. An unrelated model
   assertion must not become a verified fact because its attached quotation exists.
   Preserve useful summaries and labelled hypotheses.
3. Prevent unsupported quantities from entering approved model output. Cover small
   integers, written quantities, percentages and genuine numbers reused in the wrong
   context. A broader regex alone does not establish attribution. Use constrained,
   evidence-linked factual spans or another bounded, tested design; document residual
   semantic limits and retain human review.
4. Reject or explicitly mark unresolved claims rather than silently manufacturing a
   successful model result. Retrieval failure stays distinct from poor fit. Failed
   demonstrations cannot support success claims.
5. Correct README, UI, SECURITY and acceptance wording. Suggested bounded description:
   "SalesDesk links research to captured sources, checks demonstration outputs against
   expected results, and presents outreach for human review."
6. Keep a concise mechanism/evidence/limitation table. Existing test names do not prove
   guarantees; do not build a documentation-checking framework as a milestone.

Acceptance: both reproduced false claims cannot appear as verified/approved output;
supported counterparts work; ownership, budgets and sandbox checks still pass;
documentation describes checks accurately without claiming universal factuality.

## Phase 2: complete one useful live sales journey

Needs: a concrete owner-approved model budget and the controller-only credential.

Prepare one bounded proposal covering live debugging and the small Phase 4 evaluation:
exact model(s), current rates, per-call bounds, total requests/tokens/cost, permitted
retries and configuration adjustments. Request only missing authorization once concrete;
continue independent work while waiting. Approval of this document is not spending approval.

The previous four-request and sixteen-request JSON proposals are historical, unapproved
proposals. The original two-request ledger is exhausted; never reset it. Current code
caps plans at six requests / 131,072 tokens. Preserve those guards unless an explicitly
approved envelope requires a reviewed, tested change. If using bounded batches, enforce
the aggregate authorization across all batches.

1. Verify current provider compatibility and sanitized diagnostics offline. Do not guess
   the earlier malformed-response cause or relax contracts merely to pass.
2. Run the synthetic freight-company sample through live research synthesis and outreach,
   using bounded inputs and the sandbox demonstration when justified.
3. Review factual support, specificity, relevance and useful copy. Schema validity alone
   is insufficient.
4. Preserve receipts, provenance, usage, outputs and execution evidence. Fixture replay
   stays available and labelled; it cannot substitute for live success.

Acceptance: one complete prospect record has successful live research and outreach,
source-supported factual content, a justified demonstration decision, actual validated
execution when run, and an editable draft passing the documented usefulness review.
A rejected response is a diagnostic result: this milestone remains incomplete.

Generated code is a separate improvement, not a prerequisite. An honestly labelled
prewritten extractor can demonstrate the supported offering. Do not turn the first sales
milestone into another general code-generation project.

## Phase 3: make the sales product accessible to judges

Prepare alongside Phase 2, without waiting for the evaluation study. Public activation
needs the concrete hostname, HTTPS configuration, access policy and reviewed public
content approved. Implement and test the configuration before requesting activation.

- Use the existing Vultr VM with rollback; no new VM or managed service required.
- Main flow: offering/prospect → researched opportunity → demonstration decision/result
  → editable outreach → review. Technical receipts belong in secondary evidence views.
- Prepare synthetic-only public mode with strict quotas and fixed sample scenarios.
  Real-URL research stays private unless an explicit allowlist/access policy is approved.
- Label public replay. Live public inference needs a separate explicit budget and a
  protected controller credential; never expose an unrestricted paid endpoint.
- Export selected sanitized evidence separately from private stores. Never serve
  arbitrary ledger, session, prospect or filesystem paths as judge-facing records.
- Present the proposed URL, exact access/provenance behavior, resource costs, checks,
  rollback and cleanup ownership before requesting missing activation authorization.

Acceptance after authorized activation: a signed-out visitor completes the sample sales
journey over HTTPS; ownership, quotas and evidence boundaries hold on the public app;
the mode is truthful; STATUS.md records the URL and observed checks.

## Phase 4: small usefulness evaluation

Needs: Phase 2 success and capacity in the approved evaluation envelope. This is not a
prerequisite for preparing the public app or submission materials.

Use the three labelled synthetic scenarios and up to five public company sites spanning
strong and weak evidence. The executor can propose sites with selection reasons;
owner-supplied names are not required to prepare the set. Never send the resulting drafts.

| Question | Evidence and outcome |
| --- | --- |
| Does the source support the claim? | Quote, context, entity and supported/unsupported/unclear verdict |
| Is the opportunity specific and plausible? | Offering, prospect evidence and reasoning |
| Does the demonstration help? | Relevance decision, actual result and limitations |
| Is the outreach usable? | Use / edit / discard, reasons and concrete edits |

Identify the reviewer. Executor review is not human seller evaluation; record owner
feedback separately when available. Separate factual support, contract rejection and
usefulness. Rejection does not establish falsehood; acceptance does not establish truth.
Do not claim blocked responses "would have shipped" without a measured comparison.

Also record fetch failures, usage, estimated inference cost versus reservations, and
observed run latency. Label rule-based inference as $0 model usage, not zero total
infrastructure cost. Separate synthetic/public-site results and disclose selection bias,
sample size, missing outcomes and null results.

Acceptance: docs/measurement.md links reported results to permitted evidence and states
the review method and limits. No unsupported generalization or ROI claims.

## Phase 5: submission package

Draft alongside verification; finalize against actual behavior. Require Phases 1, 2 and
the public Phase 3 journey for our intended AI-sales-agent demo. Phase 4 strengthens the
business-value story but must not obstruct packaging or activation. If live inference
remains unsuccessful, report that gap and seek a positioning decision rather than
quietly calling a rule-based demo the completed AI agent.

Prepare video, slides, cover, README and form copy around the salesperson's task, the
opportunity found, the evidence-backed draft, and what execution adds. Show one relevant
failure/refusal and its effect on the output; technical detail remains secondary.
Confirm actual submission format and deadline in the organizer's current form.

Acceptance: materials match deployed behavior/provenance, GitHub setup is reproducible,
the public URL works signed out, and the official receipt is recorded only after
an authorized submission. Drafting does not authorize publication or submission.

## Deferred

MCP, learned memory, microVM migration, CRM, mailbox, Slack, bulk discovery and automatic
sending remain outside this entry. New demonstration families and generated-code quality
work follow a useful sales journey, not the reverse.

## Next session and authorization boundaries

- Start Phase 1 and prepare the consolidated Phase 2/4 proposal. Continue authorized
  implementation and verification without asking about routine edits.
- Preserve uncommitted work. The next session owns contract corrections, related tests,
  UI wording and docs; do not run a competing implementation session on those files.
- Update `.env.example` placeholders as needed. A historical session reported a tool
  restriction; do not assume it applies now. Never overwrite the real `.env`. Report
  actual tool rejections with their reason.
- Commit reviewed changes according to contributor guidance; public push, ingress and
  submission retain applicable publication boundaries. Do not stage unrelated files.
- Record implementation, live validation, private deployment, public activation and
  submission separately. Leave concrete next actions and unresolved failures.
