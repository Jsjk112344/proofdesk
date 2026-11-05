# Inference: contracts, diagnostics, observed outcomes and the next plan

Vultr Serverless Inference is SalesDesk's chosen live model adapter. It is an
implementation choice; Powering the Future of Work does not require inference. No other
provider is implemented and there is no fallback. Nothing in this document authorizes a
paid request.

## Separate validated contracts

One bounded transport, usage accounting and budget ledger serve three contracts. Each
request names its contract in the receipt and only that validator sees the content.

| Contract | Used by | Request options | Accepts |
| --- | --- | --- | --- |
| `python_source` | CLI code-generation workflow | optional `reasoning` controls | Non-empty source without NUL bytes or a leading Markdown fence, ≤ 32 KiB; still runs only in the sandbox |
| `research` | Prospect research step | `reasoning: {"enabled": false}`, `response_format: {"type": "json_object"}` | Brief JSON whose source ids are fetched sources and whose excerpts are verbatim page text; each claim's text must be a restatement built only from its own quotation's words and numbers (`interpretation_not_grounded` otherwise); summary, hypothesis, unknowns and relevance reason may not contain quantities absent from the quotations (`unsupported_quantity`) |
| `outreach` | Prospect drafting step | same | Body paragraphs citing only known claim ids; a quantity (numeral, written number, quantifier, percentage, amount) must appear counting the same thing in an excerpt the paragraph cites, the offering or a verified demonstration (`unsupported_quantity` with `quantity_kind` and `attribution`); no savings language, named greetings or demo mentions without a verified demonstration |

Sales prose never passes through the source validator and source never parses as sales
JSON. In live mode the controller re-derives claim strength from the validated excerpts and
applies its own demonstration rule; the model's `demo_relevance` is recorded, not obeyed.

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

## Consolidated live-debug and evaluation proposal (awaiting authorization)

This single proposal supersedes the four-request and sixteen-request files of 2026-11-05,
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
