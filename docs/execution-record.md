# Local execution record v2

[execution-record.schema.json](execution-record.schema.json) is the JSON Schema 2020-12
contract for new records. Historical v1 records from `95b67b5` remain unchanged; they
predate model provenance and safe input rejection. There is no automatic migration.
Everything stays under ignored `.local/`; records are local evidence, not a database,
authenticated audit log or power-loss durability guarantee.

## Task execution records

`.local/executions/<uuid>/record.json` is saved before dispatch and atomically finalized
as `succeeded`, `failed` or `interrupted`. Crash recovery changes unfinished work to
`failed` / `controller_abandoned` after container cleanup. `execution_kind=local_docker`
identifies the intended runner, not proof of dispatch.

| Fields | Meaning |
| --- | --- |
| `schema_version` | 2 for newly written task records |
| `id`, `container_name`, timestamps, `scenario` | Task identity, UTC times and controller case label |
| `source_kind` | `deterministic_synthetic_fixture`, `offline_provider_fixture`, or `vultr_model_generated` |
| `generation` | Null for deterministic fixtures; otherwise workflow ID, attempt 1/2, provider, model, request/response hashes and generation receipt path relative to that workflow |
| `revision` | Git commit and dirty flag at task start |
| `dispatched` | Controller entered the runner; persisted before that call, not proof task code started |
| `input_rejection` | Null or bounded byte counts and per-field limit for pre-dispatch rejection |
| `input_sha256`, `script_sha256`, `expected_sha256` | Hashes of saved exact input/source and canonical expected JSON; null on input rejection |
| `image`, `evidence.image_id` | Requested pinned image digest and resolved platform image identity |
| `limits`, `evidence.policy`, `evidence.preflight` | Controller limits, inspected Docker policy, pre-task kernel/environment readback |
| `evidence.container_name` | Attempt-specific runner identity after readiness check |
| `exit_code`, `failure_reason` | Null if not observed; stable task, validation, deadline or infrastructure failure |
| `validated_artifacts` | Accepted bytes only: fixed path, MIME type, size, hash and controller validation contract |
| `cleanup` | Verified absence after attempted dispatch, or `removed=true, reason=not_started` for pre-dispatch rejection |
| `probe_check` | Optional CLI expected outcome and synthetic canary hashes, separate from task success |

Scripts/inputs over 32 KiB are rejected **before saving their contents or hashing them**.
The directory contains only `record.json`, with `task_input_limit`, no input/source/expected
hash, `dispatched=false`, empty evidence and null exit code. The controller never reads
runner evidence or calls its cleanup for that rejection. `not_started` is not a Docker
absence observation. Success → rejection → success on the same runner is regression-tested.

Admitted tasks save `input.txt`, `script.py` and `expected.json`. `task.log` contains bounded
untrusted stdout/stderr when available; timeout/output-limit paths retain failure reasons
and discard incomplete output. Unvalidated archives are discarded without extraction.
Only accepted bytes go to fixed `result.json`; JSON must exactly match the controller's
expected keys, types, nested structure and values. The validation label is
`exact_controller_schema_and_content`, including for fixture execution.

Exit zero with incorrect output remains a failed task, with no validated artifact.
Missing Docker leaves a null exit code and unverified cleanup after runner entry; there
is no host fallback. Cleanup failures remain terminal even if output validated, and do
not erase the original task's failure reason. The workflow records the cleanup stop.
Schema constraints require successful tasks to have exit 0, accepted output and cleanup.

## Workflow and generation evidence

`.local/workflows/<uuid>/record.json` uses its own `schema_version=1` and stores workflow
identity, controller revision, timestamps, provider, model config, approval metadata (or
null), budget snapshot, status/failure and at most two attempt entries. Each attempt lists
its generation receipt and separate execution IDs with case/held-out labels. No request
or execution is silently repeated. A failed second attempt retains both generations and
all completed task records. This workflow format is documented here; the linked JSON
Schema describes task execution records only.

Each `attempt-N/generation.json` has generation schema version 1:

| Fields | Meaning |
| --- | --- |
| `provider`, `endpoint`, `config` | `offline_fake_provider` with no endpoint, or `vultr_serverless_inference` with the fixed endpoint; explicit model/deadline/token/byte bounds |
| `status`, `failure_reason`, timestamps, `elapsed_seconds` | Request lifecycle and stable sanitized reason |
| `dispatched` | Request may have been sent; persisted before the provider call |
| `request_sha256` | Hash of exact bounded request JSON, excluding HTTP credentials |
| `response_sha256`, `response_bytes`, `http_status`, `provider_response_id` | Bounded response metadata when available; absent on transport/oversize failure |
| `usage`, `usage_kind` | Integer reported prompt/completion/total tokens, or null; `synthetic` for fake responses, `provider_reported` for Vultr |
| `reservation`, `budget` | Worst-case allowance reserved before dispatch, and cumulative budget snapshot; not an invoice |

`request.json` is saved after input admission/reservation. A protocol-valid bounded
response saves exact `response.json` and `script.py`, allowing both response and execution
source hashes to be checked. Malformed/oversized responses save no returned content;
error bodies are discarded. Raw exceptions/credentials never become receipt diagnostics.
A source script can still be wrong; only Docker execution and controller validation can
establish the task's result.

The approval ledger under `.local/model-budgets/` persists reservations across invocations.
Failed or uncertain requests never refund capacity. The ledger can be more conservative
than a request receipt if a crash occurs between reservation and dispatch. Explicit
recovery marks pending requests/workflows abandoned and reconciles budget summaries with
the ledger, without automatic resend. See [inference configuration](inference.md).

Offline receipts and generated-response fixture execution are real local orchestration
and Docker observations, with synthetic usage and canned source. They do not establish
model reasoning, live Vultr compatibility/billing, deployment or general escape protection.

## Generation receipt v2 and prospect records (2026-11-05)

`generation.json` now has `schema_version: 2` and names its `contract` (`python_source`,
`research` or `outreach`). Added fields: `request_options` (`reasoning`, `response_format`),
`response_keys`, `response_model`, `model_echo_matches`, `finish_reason`,
`reasoning_present`, `reasoning_chars`, `reasoning_tokens`, `content_chars`,
`content_head` and, on rejection, `diagnostic` (`stage`, `field`, `expected`, `observed`
and bounded counts). `usage_kind` is `synthetic`, `provider_reported` or
`replayed_provider_usage`. Rejected content is never saved.

`.local/prospects/<uuid>/record.json` (schema version 1) stores offering, target, owner
hash, saved events, sources (without text; text under `sources/sN.txt`), brief,
demonstration decision/result with the linked execution id, draft versions with hashes,
review state and sanitized model diagnostics. Live-mode receipts live under
`generation/<contract>/`. Prospect records link to ordinary task execution records; the
JSON Schema in this directory still describes task records only.
