# Bounded inference and a future live-run plan

Implemented 2026-11-03: controller-side Vultr chat-completions adapter and bounded
extraction workflow. Observed tests use offline canned responses only. No live model
has been selected, no credentials are needed for offline work, and authorized spend is
**$0**. The web API does not expose this workflow.

## Wire protocol and limits

The only live endpoint is `https://api.vultrinference.com/v1/chat/completions`, with a
controller-only bearer credential. The standard-library HTTPS transport performs one
POST, verifies TLS, does not use environment proxies, never follows redirects, and has
no SDK/automatic retries or fallback. A separate trusted controller process enforces the
total request deadline, including DNS, TLS, headers and body, then terminates/joins it.
It never executes returned source. Ending a client request does not prove provider-side
cancellation or eliminate a charge.

`ModelConfig` requires an explicit model identifier. Defaults/bounds:

| Setting | Default | Permitted range |
| --- | --- | --- |
| Total request deadline | 30 seconds | 1–60 seconds |
| Input token allowance | 12,000 | 256–32,768 |
| Completion token cap | 2,048 | 1–4,096 |
| Response body cap | 65,536 bytes | 1,024–131,072 bytes |
| Generated Python cap | 32,768 bytes | Fixed task-source limit |
| Requests per workflow | At most 2 | Budget can reduce to 1 |
| Script evaluation attempts | At most 2 | Second only after eligible failure |

The input admission check conservatively requires serialized UTF-8 request size plus
256 framing tokens to fit the input allowance. This is an estimate, not a tokenizer.
Verify the chosen model's tokenizer/framing against this assumption before approving
live requests. All input is synthetic text, with no media or provider tools.
`max_completion_tokens` explicitly bounds reasoning plus visible completion; responses
must finish with `stop`. Actual provider enforcement and billing have not been tested.

A response must be bounded strict JSON with one assistant source-string choice, the
requested model ID, no tool calls, a bounded response ID and integer usage counts.
The controller rejects Markdown fences, empty/NUL source, overlong scripts, missing
usage, inconsistent totals and reported token-limit breaches. It records valid integer
usage even on a breach, and never executes that response. Unknown usage remains null;
full reservations remain charged against the local allowance. Protocol-valid Python
with a syntax/runtime error is evaluated in Docker, never compiled or executed on host.

## Evaluation and correction

Generation sees one synthetic development document and a generic extraction contract.
The same source is evaluated in fresh Docker containers against three controller-owned
cases. Additional documents and all expected answers stay outside model prompts.
No validator results are accepted from model self-report. Public synthetic fixtures
are not a statistically independent benchmark or evidence of live model quality.

Only `task_nonzero_exit`, `artifact_schema_or_content_mismatch`, `malformed_artifact`
and `missing_artifact` permit one correction. Feedback includes the prior script and
stable failure code. It excludes logs, actual output, expected JSON and additional
inputs. Every attempt starts evaluation from the first case. A second failure stops.
Timeouts, quotas, unsafe artifacts, policy/infrastructure and cleanup failures stop
immediately; no later document or model call runs. Fixture commands retain their behavior.

## Before a paid request

Prepare one exact plan for owner approval, using current official model availability
and prices. This document is a template, not approval or a current price quotation.

1. Choose one available text/code-capable Vultr model ID; confirm context capacity,
   token accounting and `max_completion_tokens` support. Keep provider/model fallback off.
2. Record dated official input and output USD-per-million rates, including reasoning,
   cache assumptions, taxes/fees or subscription commitments if applicable. Use conservative
   upper rates; do not rely on unredeemed credits or presumed free failures.
3. Bind exact `ModelConfig`, maximum requests, total reserved tokens and positive cost
   cap. With the default bounds, at most two requests reserve **28,096 tokens**:
   24,000 input and 4,096 completion. There are no transport retries; the correction is
   the second request. HTTP errors, timeouts and uncertain requests retain reservations.
4. Compute the conservative API ceiling as
   `2 * (12000 * input_rate + 2048 * output_rate) / 1000000` USD, rounded upward with
   room for applicable billing terms. Any subscription/provisioning cost needs separate
   authorization; this CLI provisions nothing. Decrease request/token counts if needed.
5. Obtain only missing approval for that exact plan and cap. Save it locally with a
   unique approval reference; keep the API key in the controller environment, outside
   the file. Do not generate an approval reference on the owner's behalf.

The local approval JSON must contain exactly these fields; the placeholders below are
intentionally invalid and must be replaced only after pricing verification and approval:

```json
{
  "config": {
    "model": "REPLACE_WITH_VERIFIED_MODEL_ID",
    "deadline_seconds": 30,
    "max_input_tokens": 12000,
    "max_output_tokens": 2048,
    "max_response_bytes": 65536
  },
  "budget": {
    "max_requests": 2,
    "max_total_tokens": 28096,
    "ceiling_usd": "REPLACE_WITH_APPROVED_CAP",
    "input_usd_per_million": "REPLACE_WITH_VERIFIED_RATE",
    "output_usd_per_million": "REPLACE_WITH_VERIFIED_RATE"
  },
  "approval_reference": "REPLACE_WITH_EXACT_OWNER_APPROVAL_REFERENCE",
  "pricing_source": "REPLACE_WITH_OFFICIAL_PRICING_URL",
  "pricing_checked_at": "YYYY-MM-DD"
}
```

All config/budget fields are required. Decimal prices/cap must be finite and positive;
requests cannot exceed two. `--model` or `VULTR_INFERENCE_MODEL`, if supplied, must match
this plan. `VULTR_INFERENCE_BASE_URL`, if supplied, must equal the fixed Vultr base URL.
The CLI does not auto-load `.env` files. Missing configuration/credentials/approval stops
without sending. No paid calls are made by tests or CI.

Each request reserves its worst-case tokens and cost **before dispatch**, retaining the
reservation on all failures. The approval identity hashes its exact config, budget and
approval/pricing metadata. Its atomic ledger lives in `.local/model-budgets/<hash>.json`;
reusing the plan, even in another CLI invocation, restores consumed allowance. It is
local to this checkout and trusted controller; retain the checkout/ledger, do not copy
an approval to another checkout to reset spend. This is not an account-wide billing cap.
Deleting/modifying local state is outside the threat model. Raw provider errors are not
saved, and no billing refund is inferred from them. Actual token usage is recorded
separately from pessimistic reservations. No cloud resources require teardown here.

After an authorized live run, preserve its separately labelled workflow/execution
records, real provider usage, validation results and cleanup evidence. Do not relabel
an offline fixture pass as live evidence. A hard crash requires `cleanup`, which marks
pending work abandoned without resending requests or refunding uncertain reservations.

## Official technical references

Checked 2026-11-03 for implementation; no snippets copied:

- [Vultr chat-completion request/response contract](https://api.vultrinference.com/docs/reference/create-chat-completion)
- [Vultr request/context/output limits](https://api.vultrinference.com/docs/concepts/limits)
- [Vultr quickstart and usage accounting](https://api.vultrinference.com/docs/get-started/quickstart)

Model availability and prices must be refreshed before requesting live authorization.
