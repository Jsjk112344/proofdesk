# Acceptance criteria and observed checks

Observed checks are dated and labelled by evidence kind: **real** (actual HTTP, retrieval
or Docker execution), **offline** (unit tests with injected resolvers, recording runner
and fixture responses) or **mocked UI** (browser interaction against a mocked API).
Security claims never exceed observations.

## Dealer video preparation, observed 2026-11-06 ET

- **Real public app:** fresh Group view, saved accepted results, Run available, counter
  reset and six analysing tiles within the first 20 seconds; all 24 jobs complete.
- **Real full live inference:** 25 accepted Qwen responses, no replay or failed briefs;
  9,000 reviewed, 1,050 at risk, 1,007 best matches in stock, 792 distinct aged units,
  $3,434,800 estimated gross. The group brief uses the same in-stock count.
- **Real approvals:** Sandy/Maria facts preserved; 40-row byte-identical CRM download,
  cross-session refusal and durable schedule after tab closure. The test schedule is
  disabled afterward. See the scene manifest in docs/video.
- **Local checks:** offline suite 114 tests, seven opt-in skips. Dealer Docker
  reconciliation/cleanup passed. Broader Docker checks hit concurrent lock contention;
  the isolated signals/recovery checks passed, but the filesystem probe exceeded its
  unchanged deadline. The full containment suite is not reported as passed.

## Hackathon refactor: public acceptance

- **Live inference:** unchanged analysis, research and outreach contracts accepted actual
  Vultr responses. Prompt-only rejection corrections; receipts and accounting in STATUS.md.
- **Public HTTPS:** trusted certificate, outside-VM HTTP journey and signed-out browser
  initialization verified at salesdesk.149.28.51.139.sslip.io.
- **Seed/isolation:** one plan/run/task/prospect and two jobs per initial session, normal
  quotas, idempotent initialization, no automatic approval of visitor edits, cross-session 404.
- **Approval/walk-away:** save next move, Approve & schedule, close tab, reopen ready packet
  and download verified against the real public backend. Replay labelled honestly.
- **Checks:** 96 tests passed with Docker enabled; build/lint/format/compile passed; mocked
  browser and real public browser passed; mobile no overflow. Screenshots in docs/assets.

The dated sections below preserve earlier observations, including then-unfinished milestones.

## Historical campaign experiment and durable jobs — observed 2026-11-05 (fourth continuation)

Baseline: `ee64b08` plus this session's uncommitted work. Local host: macOS with Colima
Docker Engine 29.5.2, Linux/arm64; VM: Ubuntu 24.04 x86-64, Docker 29.1.3. Interpretation
mode for every real check was **rule-based (no model)**; live mode was exercised offline only.
No paid request was made.

| Criterion | Evidence | Observed result |
| --- | --- | --- |
| Pinned file imports with 64,000 rows and the documented arm counts; changed checksum, invalid arm, non-finite spend, non-binary outcome, missing value rejected visibly | real (local and VM import) + offline | Arms exact (Mens 21,307/3,894/267/$30,311.69; Womens 21,387/3,238/189/$23,038.11; No E-Mail 21,306/2,262/122/$13,908.33); `dataset_checksum_mismatch`, `dataset_size_mismatch`, `dataset_header_rejected`, `dataset_value_rejected` with column and observed class |
| Equal-valued rows keep multiplicity; a fixture confirms independent calculations; empty/zero-event groups defined | offline | Synthetic fixture with a duplicated row imports 20 per arm; conversion 4/20 vs 2/20 → +10.00 pp with the Newcombe interval from the controller; `wilson_interval(0, 0)` is None, `0/10` gives 0.0 to 0.2775, relative change undefined at zero control |
| Repeated analysis with identical input/plan/code/seed reproduces the same result; failed/timed-out sandbox leaves no result and is cleaned up | real Docker + offline | Identical artifact SHA-256 across two local runs, two VM runs and the local/VM pair (`3b3152bf…`); tampered counts → `reconciliation_mismatch_conversions` with no result; timeout → `task_deadline_exceeded`, cleanup removed |
| Historical assignments unchanged; invented policy refused | offline + real API | `comparison.treatment = new_random_policy` → 409 `invalid_plan_comparison`; identical arms and extra keys refused; the sandbox echoes and the controller checks the plan hash |
| Numeric AI references resolve only to metrics; unknown ids, invented ROI, unauthorized actions and malformed output rejected; valid reasoning accepted with provenance | offline | `unknown_metric_id`, `unsupported_quantity`, `invented_roi_or_outcome`, `unauthorized_action`, `keys_mismatch`, `unparseable`; a fixture live response is accepted with provenance `live_model`, usage logged separately from the reservation; the rule-based reading passes the same contract |
| Approval binds to the exact version; editing invalidates; cross-owner, credential and unapproved dispatch refused | offline + real HTTP (local and VM) | Approval with the previous proposal hash → 409; edit after approval → task `pending_review`, scheduled job cancelled; tampered approval hash → worker `approval_stale`, task failed, no packet; other session → 404 for plan, job, artifact, packet, cancel; the model prompt contains no credential or rows |
| A scheduled job runs after browser closure and survives a worker restart; duplicate dispatch creates no second artifact; cancellation and exhausted budgets prevent dispatch | real HTTP (local and VM) + offline | Packet job due 15–20 s later ran with the client absent; `systemctl restart proofdesk` during the analysis job → `interrupted_requeued`, attempt 2 succeeded, one artifact; a stale lease token writes nothing; cancelled task's job cancelled; `model_budget_exhausted` keeps the statistical result |
| Packet preparation produces a real saved artifact bound to approved inputs; missing data reported; no model call; nothing marked launched or completed | real HTTP (local and VM) | Packet artifact with bindings (plan, run, artifact, proposal hashes), `model_call: false`, `planning_review` when inputs are missing, external prerequisites listed (`historical_email_text`, `consented_eligibility_list`), `not_claimed` statements; task reaches `ready_for_review`, completion needs human evidence |
| One browser journey source → plan → analysis → result → approval → scheduled job → packet → review | mocked UI | 18 checks passed in the disposable browser container (`.local/browser/browser-check.json`) |
| Private Vultr reproduction with a worker completing work independently of the browser; second session isolated; public limits bound queued work | real HTTP on the VM + offline | `.local/deployment/vultr-experiment-journey-2026-11-05.json`; public mode: 4th plan → `experiment_quota_reached`, 4th queued job → `experiment_queue_full`, 24-hour horizon |
| Public HTTPS readiness tested locally; public URL claimed only after a signed-out visit | offline + mocked UI | Public-mode API and browser checks pass; **no public URL is claimed**; activation awaits the hostname and approval |
| CONTRIBUTING checks | local | Ruff lint/format, compileall, 93 offline tests, 93 Docker-enabled tests, TypeScript/Vite build, publication/link scan (worktree) passed |

Not observed: a successful live Vultr model request for any contract, a public URL, a
recorded video or a submission. Those criteria remain **incomplete**.

## Contract corrections, envelope and public-demo preparation — observed 2026-11-05 (third continuation)

Baseline: the uncommitted SalesDesk working tree on `feat/local-execution-slice` (HEAD
`8413fcd`). Local host: macOS with Colima Docker Engine 29.5.2, Linux/arm64. Generation
mode for every real check was **rule-based (no model)**; live mode was exercised offline
only. No paid request was made.

| Criterion | Evidence | Observed result |
| --- | --- | --- |
| Reproduced defect 1 cannot pass: an unrelated assertion attached to a genuine quotation | offline (`test_interpretation_unrelated_to_its_quotation_is_rejected`) | "They operate a warehouse on the Moon." with a verbatim freight excerpt → `research_contract_rejected`, field `claims[0].text`, observed `interpretation_not_grounded`; the diagnostic contains no response text. Before the fix the same input passed (test failed first) |
| Supported counterparts for defect 1 | offline | The quotation itself (`text_kind: verbatim`) and a restatement using only its words ("Their back office processes the paperwork from suppliers.", `grounded_restatement`) pass; `verification: verbatim_quotation` is set on quotations; the model summary is kept as `model_summary` and never marked verified |
| Reproduced defect 2 cannot pass: an unsupported quantity in outreach | offline (`test_outreach_quantities_need_the_same_number_for_the_same_thing`) | "Your team operates 42 warehouses." → `unsupported_quantity` (`numeral`, `no_matching_number`); "forty-two warehouses" (`written`), "dozens of warehouses" (`quantifier`), "40%" (`percent`) likewise; subject lines checked the same way. Before the fix "42 warehouses" passed (test failed first) |
| Genuine numbers attributed to the wrong subject are rejected | offline | "fleet of 38 warehouses" (38 vehicles), "300 invoices" (300 suppliers), "24,000 pallets" (square metres), "2009 pallets" (founding year) → `unsupported_quantity` with `attribution: number_in_other_context`; "You serve 1600 retailers" with no verified demo → `no_matching_number` |
| Supported quantities pass | offline | "a fleet of 38 vehicles", "more than 300 suppliers", "since 2009 … two bonded warehouses", "24,000 square metres … two sites", "five days a week", and the verified demonstration's "2 line items … 1600 cents (USD 16.00)" all pass with the cited claims |
| Unsupported quantities cannot enter the brief | offline | "A 3PL running 42 warehouses." as summary → `company_summary.text` / `unsupported_quantity`; "your 42 warehouses" in the hypothesis → `opportunity_hypothesis.text` / `unsupported_quantity` |
| Existing contract, journey, ownership, quota, idempotency, recovery and API checks still pass | offline | 71 tests, 5 Docker methods skipped explicitly (4.8 s) |
| Sandbox, probes, signal recovery and web/demonstration execution still pass | real Docker | `PROOFDESK_DOCKER_TESTS=1`: all **71 tests passed in 46.8 s**; no labelled containers remained (log `.local/live-preflight/docker-tests-2026-11-05-session3.log`) |
| Aggregate envelope across batched plans | offline (`test_envelope_aggregates_batches_and_never_resets`) | Two 2-request plans under a 3-request envelope: the 4th reservation stops with `model_envelope_exhausted` before dispatch and the plan ledger does not consume; a third plan with different model settings reopens the same aggregate at 3/3; a tampered envelope ledger stops with `model_envelope_ledger_invalid`; plan files with an `envelope` block load, other extra keys are refused |
| Public demo mode | offline API (`test_public_demo_mode_restricts_targets_quotas_and_live_mode`) + mocked UI | Real URL → 409 `public_demo_samples_only`; allowlisted host admitted; session quota 3 and total 100 reported and enforced; `public_demo: true` on `/api/health` and `/api/workspace`; a private credential plus plan stays `deterministic` unless `PROOFDESK_PUBLIC_LIVE=1`. Browser: public label, disabled website field and button, sample journey completes |
| UI labels restatements and summaries; checks list no longer overstates | mocked UI | Disposable Playwright container: **11 checks passed** (landing, blocked address, research brief, demonstration, review/edit, reload, skipped demonstration, model-validation failure diagnostic, public demo mode, mobile layout, no page errors); screenshots under `.local/browser/` |
| CONTRIBUTING checks | local | Ruff lint/format, compileall, 71 offline tests, TypeScript/Vite build, publication/link scan passed |

Evidence files (ignored): `.local/live-preflight/docker-tests-2026-11-05-session3.log`,
`.local/browser/browser-check.json` and `*.png`, `.local/live-preflight/catalog-receipt-2026-11-05-session3.json`,
`.local/live-preflight/proposed-live-envelope-2026-11-05.json` and the four batch plan files.

Residual limits (documented in README and SECURITY): grounding is lexical, so a
restatement with changed word order or negation can still pass; a number reused for a
different subject that shares a head word passes; "one", ordinals and vague words are not
quantities; savings wording is pattern-based. Human review remains the final check.

Not observed: a successful live Vultr model request for any contract, live-mode behaviour
against the real provider, a public URL, or any send. Those criteria remain **incomplete**
pending the owner's authorization of the consolidated envelope and of public activation.

## Sales journey — observed 2026-11-05 (second continuation)

Baseline `8413fcd` with the previously uncommitted web/deployment work preserved. Local
host: macOS with Colima Docker Engine 29.5.2, Linux/arm64, cgroup v2, default seccomp.
Generation mode for every real check below was **rule-based (no model)**; live model
mode was exercised offline only.

| Criterion | Evidence | Observed result |
| --- | --- | --- |
| Landing asks for an offering and a prospect, not a document | mocked UI + real API | Landing form has "Your offering" and "Prospect website", no document chooser; `/api/workspace` returns capability, default offering, samples and generation mode |
| One complete supported scenario | real HTTP + real Docker | Prospect `ee7edb5d889f4bb49cf9deda667f9805`: 4 synthetic pages read, 6 verbatim claims, `run` decision, demonstration execution `319e6dba76cd49b9a501d33384482c15` verified (exit 0, total 1,600 cents, cleanup verified), evidence-backed draft v1; CLI run `f2d2c63bf0744427b718af9799d7e921` likewise |
| Weak-evidence prospect gives honest uncertainty | real HTTP retrieval | `https://example.com/` prospect `4e3d454636404b4ba839205fde85bd72`: page fetched (HTTP 200), 0 claims, `skip_insufficient_evidence`, draft states little public information and asks; synthetic sparse sample `f4084526c5b34f84b2f2b2538766c2fe` same path |
| Irrelevant prospect skips the demonstration | real Docker-free journey | Synthetic bakery `310274a8f4964e2bac26659efc9527d3`: `skip_irrelevant`, no sandbox run, draft gives one sentence of context and an open question, no extraction pitch |
| Failed demonstration never described as success | offline | Recording-runner wrong output → demo `failed` (`artifact_schema_or_content_mismatch`), draft says the example was left out; outreach contract rejects `mentions_demo` and demo words without a verified result |
| Evidence corresponds to fetched content; fabricated citations rejected | offline + real | Research contract rejects unknown source ids, excerpts not in source text, unknown claim ids and key mismatches with field-level diagnostics; rule-based claims are verbatim sentences (asserted against page text) |
| Malformed/truncated model responses give sanitized errors, no execution | offline | `finish_reason=length` with reasoning tokens → `provider_incomplete_response` with stage/field diagnostic; null content, tool call, empty choices, missing usage, non-string model, non-JSON body → `provider_malformed_response` naming the field; no `script.py`, no content in receipts |
| Missing/exhausted authorization makes zero paid requests | offline + real | Live mode without a plan stops with `live_plan_not_configured` and no receipt; missing credential/approval never calls the transport; the exhausted ledger is unchanged and the web deployment has no credential |
| Private-address redirects and hostile page instructions cannot bypass safeguards | offline + real API | Redirect to `169.254.169.254` and to a host resolving to `10.10.10.10` blocked without connecting; mixed public/private DNS answers blocked; loopback, link-local, mapped and ULA addresses blocked; redirect loops capped; hostile instruction sentences on a page change neither the decision nor the draft; real API rejects IP literals, `localhost`, `ftp://` and custom ports |
| Cross-session access denied; duplicates do not duplicate work | real HTTP | Second session gets 404 for detail, empty list and 404 for review; same request id returns the same prospect; a second start while active is refused with `another_prospect_is_active` |
| Reload restores prospect and draft; editing invalidates review | real HTTP + mocked UI | Review of v1 recorded; edit created v2 and reset review to pending; duplicate edit with the same request id kept v2; stale review refused with `draft_version_conflict`; history listing shows both prospects and draft versions after reload |
| Existing Docker containment and cleanup tests still pass | real Docker | Full suite with `PROOFDESK_DOCKER_TESTS=1`: 67 tests passed in 41.5 s, including 15 probes plus fixture, signal/crash recovery, web worker documents and generated-response fixtures; no labelled containers remained |
| Browser checks cover the journey and failure states | mocked UI | Disposable network-disabled Playwright container: landing, blocked-address message, research brief, demonstration, review/edit, reload, skipped demonstration, model-validation failure diagnostic, mobile layout, no page errors (10 checks) |
| CONTRIBUTING checks | local | Ruff lint/format, compileall, 67 offline tests, TypeScript/Vite build, publication/link scan passed |

Evidence files (ignored): `.local/live-preflight/local-web-http-2026-11-05-session2.json`,
`.local/live-preflight/docker-tests-2026-11-05-session2.log`, `.local/browser/*.png` and
`browser-check.json`, `.local/prospects/<id>/record.json`, `.local/executions/<id>/`.

Not observed: a successful live Vultr model request for any contract, live-mode behaviour
against the real provider, a public demo, or any send. Those criteria remain **incomplete**
until an authorized live run.

## Planned product criteria (unchanged intent)

- A supported demonstration executes and returns actual files, logs and check results.
- A recoverable failure is corrected within the allowed retry count (code generation only).
- A saved draft uses supported facts and identifies demonstration limitations.
- Reload retrieves the same authorized user's saved work.
- Insufficient evidence, provider failure and rejected fit remain distinct outcomes.
- Cross-user reads denied; private/metadata targets blocked; hostile pages cannot authorize
  tools, spend or sends; approval binds to exact versions; duplicates do not resend.

## Earlier observed checkpoints

### Synthetic web and private Vultr journey — observed 2026-11-05 (first continuation)

| Criterion | Observed result |
| --- | --- |
| Real Vultr inference | Two HTTP 200 responses, both rejected before code execution; incomplete completion followed by malformed response |
| Ledger continuity | Same approval identity/ledger retains 2 requests, 32,192 tokens, $0.0040384 reservation; no reset |
| Fixed web inputs | Three synthetic documents only; invalid selection/body/IDs rejected |
| Session ownership | Different session denied job read with 404 |
| Result integrity | Saved-byte hash checked before display; a changed artifact is rejected |
| Private Vultr HTTP flow | Three documents executed on the VM with totals 1,600 / 408 / 2,195 cents and verified cleanup |
| Vultr probes | All 15 probes plus final valid fixture matched expected outcomes and cleanup |

### Bounded generation workflow — observed 2026-11-03

Offline provider protocol, correction bounds, budgets, held-out withholding and provenance
labels; see git history for the full table.

### Local execution slice — observed 2026-11-03

Valid extraction, wrong-output rejection, unsafe artifacts, output quotas, deadline,
CPU/RAM/process/write limits, network isolation, host canary, credential allowlist,
lifecycle, interruption, hard-crash recovery, missing Docker and record schema; see git
history for the full table.


## Compact demo presentation

- At 1440×900, campaign answer and approval/download action, and prospect draft and
  Approve draft action, are visible without scrolling. At most one filled action is
  visible on each default page.
- Activity defaults to a labelled horizontal stepper; active jobs expand it and job
  completion collapses it. Manual expansion exposes timestamps; raw evidence stays in
  Verification. No completion text, hashes or version bindings appear by default.
- See full analysis retains every detailed reading/metric/secondary outcome. Next move
  defaults to a read-only summary, with Edit and an Advanced disclosure for assumptions.
- Draft save appears only while edited; approving/reviewing the exact saved version and
  invalidating review on edit use the existing endpoints and hashes.
- Measure default document heights in a fresh public session before and after approval;
  verify one primary action and the absence of page overflow, including mobile.

## Video v2 trace

The real-Docker Sandy test verifies trace counts against reconciled metrics and the
leased child event. Offline suite: 114 tests, seven optional Docker skips; all executed tests passed.
Public verification is recorded in the v2 video facts and manifest after deployment.

V2 public verification: deployed trace opened from Sandy's live Group tile; captured
pending and completed steps, 375 open / 40 risk / 25 cold, 117 local + 1,638 sister
cars, 70,200 scored pairs, top score 100, three Qwen drafts and 40 total drafts.
The final group succeeded without failures in 124.758 seconds. Approval reached Ready
without sends. All 85 deployed file hashes match release 1c2cf6b.

## Video v3 public presentation checks (2026-11-06 ET)

The compact UI was deployed and recorded from public HTTPS at a 1280×720 viewport,
1.5 device scale and 1920×1080 output. All 85 deployed file hashes matched. A final
24-store run succeeded in 127.493 measured seconds with 25 accepted Qwen replays,
zero new inference calls and no recording page errors. The trace, first follow-up,
Maria story/SMS, alternatives toggle and horizontal bounds passed direct browser
checks in `scripts.check_video_v3`. A completed approval adds a Ready panel; one
short scroll retains the trace and full first card together. New recorded sources
and machine-readable checks are indexed in `docs/video/REVIEW-v3.md`.

Frontend build, lint, formatting, compilation and 114 offline tests passed, with
seven optional checks skipped. Backend execution/approval contracts did not change;
this check does not claim a new Docker containment acceptance.
