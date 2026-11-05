# Acceptance criteria and observed checks

Observed checks are dated and labelled by evidence kind: **real** (actual HTTP, retrieval
or Docker execution), **offline** (unit tests with injected resolvers, recording runner
and fixture responses) or **mocked UI** (browser interaction against a mocked API).
Security claims never exceed observations.

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
