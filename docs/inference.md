# Dealer analyst contracts: current surface

The dealer workflow uses **rooftop_brief** and **group_brief** with the existing Vultr-only
transport, pessimistic reservations, aggregate envelope, diagnostics and exact-input replay.
Model: `qwen3.8-flash-next`; JSON-object output; reasoning disabled. Authenticated catalog
checked 2026-11-06: $0.10 input / $0.20 output per million tokens. The full sample's dealer
contracts passed live; request, usage and uncertainty accounting is in [STATUS.md](../STATUS.md).

`SALESDESK_DEALER_LIVE_PLANS` names an operator-only directory with `r01.json` through
`r24.json` and `group.json`. Each uses the authorization schema documented below: maximum
six requests and 108,288 reserved tokens per plan, shared $0.15 / 64-request / 1,048,576-token
envelope. No per-request approval is needed within the standing owner authorization.
Keys stay outside the release; templates and source files contain no credentials.

The model receives validated aggregate metrics and curated top-lead facts, not CSV exports,
notes, contact details or salesperson names. Every quantity and vehicle/name fact in a draft
uses a `[metric:KEY]` or `[field:KEY]` reference rendered by code. The validator requires
known top leads and best-match stock, bounded lists, SMS at most 320 rendered characters,
known references, first-name greeting and `[Salesperson]`, and restrictive message vocabulary.
It refuses unsupported features, guarantees/discount promises and sending language.
These lexical contracts constrain drafts; managers still review their meaning and suitability.

Qwen prepares top-lead drafts; additional drafts have **Template** provenance, and saved
human changes have **Your edit** provenance. A failed live brief is visible, preserves
validated metrics and never becomes a silent template/model-provider fallback.

Per-plan process locks protect read/reserve/write across concurrent sessions; each rooftop
can call in parallel, sharing the aggregate ledger's existing cross-process lock. Attempt
receipt directories are unique. Rejected response text is neither stored nor executed.
Public samples show accepted saved results immediately. Run now executes real Docker work;
identical model input replays an accepted response through validation with `saved_replay`
provenance and a cached-response tooltip. Stable serialization sorts tied rooftop inputs.
Do not run disconnected copies of the same spend ledger on concurrent hosts: this release
handed authority from the stopped local acceptance server to the existing Vultr VM.

## Historical engine contracts and authorization schema

The sections below preserve the earlier campaign/prospect implementation and its dated
observations. The dealer workflow reuses this engine; its current spend is in STATUS.md.

# Current live verification: hackathon phase 1

Authenticated GET `/v1/models` on 2026-11-05 ET selected **qwen3.8-flash-next**.
It supports JSON-object output and optional reasoning; live calls with
`reasoning: {"enabled": false}` and `response_format: {"type": "json_object"}`
passed the unchanged analysis, research and outreach contracts. Rates remain $0.10/$0.20
per million input/output tokens. The benchmark ran through the real Docker worker;
the prospect example uses labelled synthetic pages and a real Docker demonstration.

Thirteen reservations total $0.0261248; twelve observed responses imply $0.0039680 token
cost. One interrupted harness reservation has no observed usage and is retained in full.
See STATUS.md for aggregate accounting and the $150 owner cap. Fresh batch plans share a
$0.15 inference sub-envelope; historical exhausted ledgers are never reset.

Public sessions use live mode with exact-input accepted replay preferred. Replays pass
validation again, carry `saved_replay` provenance, and reserve no paid capacity. Different
inputs call Vultr. Provider/contract failures remain visible; no silent fallback occurs.

# Inference: contracts, diagnostics, observed outcomes and the next plan

Vultr Serverless Inference is SalesDesk's chosen live model adapter. It is an
implementation choice; Powering the Future of Work does not require inference. No other
provider is implemented and there is no fallback. The owner authorized hackathon spend in AGENTS.md; the dated proposals below remain historical.

## Separate validated contracts

One bounded transport, usage accounting and budget ledger serve three contracts. Each
request names its contract in the receipt and only that validator sees the content.

| Contract | Used by | Request options | Accepts |
| --- | --- | --- | --- |
| `python_source` | CLI code-generation workflow | optional `reasoning` controls | Non-empty source without NUL bytes or a leading Markdown fence, ≤ 32 KiB; still runs only in the sandbox |
| `research` | Prospect research step | `reasoning: {"enabled": false}`, `response_format: {"type": "json_object"}` | Brief JSON whose source ids are fetched sources and whose excerpts are verbatim page text; each claim's text must be a restatement built only from its own quotation's words and numbers (`interpretation_not_grounded` otherwise); summary, hypothesis, unknowns and relevance reason may not contain quantities absent from the quotations (`unsupported_quantity`) |
| `outreach` | Prospect drafting step | same | Body paragraphs citing only known claim ids; a quantity (numeral, written number, quantifier, percentage, amount) must appear counting the same thing in an excerpt the paragraph cites, the offering or a verified demonstration (`unsupported_quantity` with `quantity_kind` and `attribution`); no savings language, named greetings or demo mentions without a verified demonstration |
| `analysis` | Experiment interpretation step (`backend/app/experiments/reasoning.py`) | `reasoning: {"enabled": false}`, `response_format: {"type": "json_object"}` | Reading JSON (question answered, interpretation, alternative explanations, unknowns, proposed next experiment with hypothesis, variants, audience requirements, unit, outcome, window, decision rule, missing inputs). Numbers may appear only as `[metric:ID]` placeholders resolving to validated metrics (`unknown_metric_id`); any digit, percent or currency symbol in prose (`unsupported_quantity`), ROI/profit/guarantee/realized wording (`invented_roi_or_outcome`) or an action that contacts the historical records (`unauthorized_action`) is refused. The controller renders values, denominators and intervals in code |

Sales prose never passes through the source validator and source never parses as sales
JSON. In live mode the controller re-derives claim strength from the validated excerpts and
applies its own demonstration rule; the model's `demo_relevance` is recorded, not obeyed. The
analysis contract receives validated aggregate metrics and documented limitations only (never
raw rows, credentials or contacts); a model cannot change source rows, methods, confidence
levels, allocation, task approval or job destinations, and a failed live step leaves the
statistical result intact with the sanitized diagnostic (no rule-based substitution). These are
lexical checks; they do not establish that an interpretation is right.

## Sanitized diagnostics

Receipts (`generation.json`, schema version 2) record, for every request: `contract`,
`request_options`, `http_status`, `response_bytes`, `response_sha256`, `response_keys`,
`provider_response_id`, `response_model`, `model_echo_matches`, `finish_reason`,
`reasoning_present`, `reasoning_chars`, `reasoning_tokens` (from
`completion_tokens_details`), `content_chars`, `content_head`
(`empty`, `markdown_fence`, `json_like`, `python_like` or `prose`), `usage`, `usage_kind`
and, on rejection, a `diagnostic` with `stage` (`envelope`, `usage`, `choice`, `message`,
`content`, `contract`), `field` path, `expected`, `observed` type or marker and bounded
counts (for quantities: `quantity_kind` and `attribution`, either `no_matching_number` or
`number_in_other_context`; for restatements: `ungrounded_lexemes`). Content, prompts and
credentials are never written to a diagnostic. Known failure shapes are reproduced offline
in `backend/tests/test_sales.py` (`DiagnosticTests`, `ContractTests`).

## Documented protocol compatibility changes (2026-11-05)

Checked against the [official chat-completion contract](https://api.vultrinference.com/docs/reference/create-chat-completion)
and [reasoning concept](https://api.vultrinference.com/docs/concepts/reasoning):

- The response `model` "may differ from request". The adapter now records the echo and
  `model_echo_matches` instead of rejecting a mismatch as malformed. A non-string model is
  still malformed.
- Reasoning text arrives in `message.reasoning`; `completion_tokens` includes reasoning
  tokens and `completion_tokens_details.reasoning_tokens` reports them. Both are recorded.
  The documented way to disable thinking, `reasoning: {"enabled": false}`, is used for the
  sales contracts; `effort` `minimal`/`low` with a bounded `max_tokens` remains allowed.
- `response_format: {"type": "json_object"}` is a documented parameter and is used for the
  JSON contracts. No other response-format shape is permitted.

Validation was not weakened elsewhere: Markdown fences, tool calls, missing usage,
inconsistent totals, non-`stop` finish reasons and oversize bodies still fail closed, and
rejected content is never executed or stored.

## Observed live outcomes — 2026-11-05 (code-generation workflow, before these changes)

| Request | Workflow ID | Provider result | Reported usage | Execution |
| --- | --- | --- | --- | --- |
| Initial | `985e8177be3b44828a04507c6e00d57e` | HTTP 200, `provider_incomplete_response` | 360 input + 4,096 completion | None |
| Separately approved follow-up | `6a7535b5c2714dfc948fc31d4b7e4fc0` | HTTP 200, `provider_malformed_response` | 348 input + 1,091 completion | None |

The first response reached the whole 4,096-token completion cap with `finish_reason` other
than `stop`; with the new receipt fields a repeat would also show whether reasoning tokens
consumed the cap. The second response was rejected by the then-current validator, which
did not retain content or a field-level diagnostic. **Its root cause remains unknown.** The
documented model-echo behaviour above is one documented possibility among several
(fence, empty content, tool call, usage shape) and has not been established as the cause.

Ledger `95977722843a1e73f60b836ec4898f6400702edc8028f4bf4d15fb245736a8e6` records 2
requests, 32,192 reserved tokens and **$0.0040384** reserved under the $0.02 cap; the
usage-priced estimate is $0.0011082. It is exhausted, was not reset, deleted or reused,
and is not a billing receipt.

## Consolidated proposal for the analysis contract and the prospect live-debug batch (awaiting authorization)

Prepared in the fourth continuation of 2026-11-05 as the single current proposal. Rates were
re-read from the public catalog on 2026-11-05 (receipt
`.local/live-preflight/catalog-receipt-2026-11-05-session4.json`, byte-identical to the
session-3 receipt): `qwen3.8-flash-next`, $0.10 / $0.20 per million input/output tokens.

| Setting | Proposed value |
| --- | --- |
| Model | `qwen3.8-flash-next` (no fallback, no other model) |
| Analysis request | 60 s deadline, 16,000 input / 1,536 completion tokens (byte-based admission; the measured prompt is about 13 KiB), 65,536-byte response, reasoning disabled, JSON-object output, temperature 0 |
| Analysis worst case per request | 17,536 tokens, **$0.0019072** |
| Batch A: analysis live validation | `proposed-batch-A-analysis-2026-11-05.json`: ≤ 6 requests, ceiling $0.012 (worst case $0.0114432): one local run and one run on the private Vultr deployment of the Mens-vs-No-E-Mail plan, with up to four further attempts after diagnosed rejections (prompt/option adjustment only) |
| Batch B: prospect live debugging (optional, separately approvable) | `proposed-batch-B-sales-debug-2026-11-05.json`: ≤ 6 requests, ceiling $0.015 (worst case $0.0120576), the earlier research + outreach debug of the sample scenario; not required for the experiment milestone |
| Envelope (aggregate) | **12 requests, 213,504 tokens, worst case $0.0235008, requested ceiling $0.03**, enforced across both batches by the envelope ledger |
| Retries | None at transport or HTTP level; every attempt is one counted request; a rejected analysis response keeps the statistical result and records the diagnostic |
| Permitted adjustments without new authorization | Prompt wording in `reasoning.py`; `reasoning` disabled or low/minimal with ≤ 1,024 tokens; analysis completion cap 1,024–2,048 and input allowance ≤ 16,000 within the same envelope |
| Not permitted | Other models, non-zero temperature, provider fallback, resetting or deleting any ledger, plans that do not name the envelope, public live mode |

Files (ignored, unapproved, `approval_reference` empty): `.local/live-preflight/proposed-analysis-envelope-2026-11-05.json`
with the two batch plan files. The controller refuses them while unapproved (`invalid_envelope`).
The owner approves by writing the same reference into the envelope block and into each batch
file that is approved; batch B may stay empty. The approved batch A file is then named by
`PROOFDESK_ANALYSIS_LIVE_PLAN` (locally via `.env`; on the VM via a root-only systemd drop-in
together with the credential). Actual usage is logged per receipt separately from the
reservation. Successful live interpretation is an explicit AI milestone; test fixtures and the
rule-based reading do not demonstrate it. **Not approved; no live request has been sent under
these files.**

The earlier 22-request / $0.05 proposal below covered the prospect contracts only and remains a
historical, unapproved proposal.

## Earlier consolidated live-debug and evaluation proposal (historical, unapproved)

This single proposal superseded the four-request and sixteen-request files of 2026-11-05,
which remain historical, unapproved proposals. Rates were re-read from the public catalog
on 2026-11-05 (receipt `.local/live-preflight/catalog-receipt-2026-11-05-session3.json`,
byte-identical to the earlier receipt): `qwen3.8-flash-next`, $0.10 / $0.20 per million
input/output tokens, 262,144-token context, `reasoning` and `response_format` supported.

| Setting | Proposed value |
| --- | --- |
| Model | `qwen3.8-flash-next` (no fallback, no other model) |
| Per request | 60 s deadline, 16,000 input / 2,048 completion tokens (byte-based admission), 65,536-byte response, reasoning disabled, JSON-object output, temperature 0 |
| Per-request worst case | 18,048 tokens, **$0.0020096** |
| Batch 1: live debugging | Sample scenario `harbor-vale-freight`: research + outreach, with up to two further attempts of each contract after a diagnosed rejection; ≤ 6 requests, ceiling $0.015 |
| Batches 2–4: usefulness evaluation | Three synthetic scenarios (6), public sites 1–3 (6), public sites 4–5 (4); 16 requests, ceilings $0.015 / $0.015 / $0.01 |
| Envelope (aggregate) | **22 requests, 397,056 tokens, worst case $0.0442112, requested ceiling $0.05**, enforced across all batches by the envelope ledger |
| Retries | None at transport or HTTP level; every attempt is one counted request; a rejected response stops that prospect |
| Permitted adjustments without new authorization | Prompt wording; `reasoning` disabled or low/minimal with ≤ 1,024 tokens; `response_format` json_object/text; completion cap 1,024–4,096 and input allowance ≤ 16,000 within the same envelope |
| Not permitted | Other models, non-zero temperature, provider fallback, resetting or deleting any ledger, plans that do not name the envelope, public live mode |

Files (ignored, unapproved, `approval_reference` empty): `proposed-live-envelope-2026-11-05.json`
and `proposed-batch-{1-live-debug,2-evaluation-a,3-evaluation-b,4-evaluation-c}-2026-11-05.json`
under `.local/live-preflight/`. The owner approves by writing the same reference into the
envelope block and into each batch file that is approved; unapproved batches stay empty and
the controller refuses them. Until then live mode sends nothing: a missing plan or credential
stops before dispatch with `live_plan_not_configured`, `missing_vultr_credentials` or
`live_spending_not_authorized`.

### Aggregate envelope enforcement

A plan file may carry an `envelope` block (`reference`, `max_requests`, `max_total_tokens`,
`ceiling_usd`). `Authorization.bind_budget` binds the envelope ledger
(`.local/model-budgets/envelope-<identity>.json`) before the plan ledger; every reservation
is checked and written against the envelope first under a file lock, then against the plan,
so batching cannot exceed the owner's total and a plan with changed model settings reopens
the same aggregate ledger with its counters intact. Failures never refund; a tampered or
inconsistent envelope ledger stops with `model_envelope_ledger_invalid`; exhaustion stops with
`model_envelope_exhausted` before any request is sent. Receipts and prospect records carry
the envelope state next to the plan budget. The offline test
`test_envelope_aggregates_batches_and_never_resets` covers two plans sharing an envelope, a
third plan with different model settings, reopening, tampering and plan-file loading.

After an approved run: preserve the prospect record, its `generation/*/generation.json`
receipts, both ledgers and any sandbox evidence; label outputs `live_model`; never relabel
rule-based or replayed output as live. A rejected response is a diagnostic result and leaves
the Phase 2 milestone incomplete.

## Wire protocol and limits

The only live endpoint is `https://api.vultrinference.com/v1/chat/completions` with a
controller-only bearer credential. The standard-library HTTPS transport performs one POST,
verifies TLS, ignores environment proxies, never follows redirects and has no SDK or
automatic retries. A killable controller process enforces the total deadline including DNS,
TLS, headers and body. `ModelConfig` bounds: deadline 1–60 s, input allowance 256–32,768,
completion cap 1–4,096, response 1,024–131,072 bytes. A plan may hold up to six requests
and 131,072 reserved tokens. Input admission uses serialized UTF-8 bytes plus 256 tokens
as a pessimistic token estimate, not a tokenizer. Each request reserves its worst case
before dispatch; failures never refund.

## Official references

Checked 2026-11-05: [chat-completion contract](https://api.vultrinference.com/docs/reference/create-chat-completion),
[reasoning](https://api.vultrinference.com/docs/concepts/reasoning),
[limits](https://api.vultrinference.com/docs/concepts/limits),
[public model metadata](https://api.vultrinference.com/v1/models/qwen3.8-flash-next).
