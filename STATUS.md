# Project status

Product name: **SalesDesk** (renamed from ProofDesk on 2026-11-05). Existing operational
identifiers and dated historical entries retain their original names.

Current checkpoint: hackathon refactor in progress. Phase 0 committed; phase 1 live
contracts verified. Public activation and the two-door UI follow in order.

## Hackathon phase 1: 2026-11-05 ET

- Owner authorization: $150 aggregate of $200 credit for inference and compute; public
  activation authorized. Deadline supplied by owner: Nov 8, 18:00 ET; target 16:00 ET.
- Authenticated model catalog GET succeeded. Selected `qwen3.8-flash-next`, JSON-object
  output and reasoning disabled. Catalog rates: $0.10 input / $0.20 output per million tokens.
- Genuine benchmark executed in Docker and accepted live analysis observed. Research and
  outreach accepted live on the labelled Harbor Vale synthetic scenario, with a verified
  Docker demonstration and an unsent draft. No validator changes.
- Prompt iteration resolved excessive summary length, unsupported quantities, and forbidden
  outcome wording (including negated wording). Final analysis and both prospect contracts passed.
- Accounting so far: 13 durable request reservations ($0.0261248 worst case), 12 responses
  with usage ($0.0039680 estimated token cost). One interrupted harness reservation has no
  observed provider usage and remains charged at its full reservation. Prior exhausted
  ledger remains untouched ($0.0040384 reserved). These are estimates, not billing receipts.
- Inference sub-envelope: $0.15, 64 requests, preserving existing six-request batch limits;
  analysis debugging stays under the owner's 40-request limit. No new compute provisioned.
  Existing VM accrual/credit balance has not been verified against account billing.
- Public workers prefer accepted responses for identical serialized inputs, revalidate
  through the same contracts, label replay, and reserve no paid capacity for cache hits.
  Timestamp metadata remains in sources but is excluded from research prompt identity.
  Different inputs use Vultr; genuine failures remain visible, with no silent substitution.
- Checks: Ruff, formatting, compileall, frontend build, repository links/patterns passed;
  offline suite 93 tests, six Docker skips; new replay test passed separately. Live Docker
  benchmark and prospect execution passed. An initial operator harness failed before
  completing inference; corrected to an isolated store with guarded subprocess entry.
- Private VM SSH and health verified; public ingress not activated yet.

## Initialization checkpoint: 2026-11-03

- Track: Blast Radius Zero (working choice from the project discussion).
- Rules checked: official event, LabLab terms and rule book on 2026-11-03.
- Existing-code baseline: empty new repository; original scaffold and planning only.
- Repository publication: https://github.com/Jsjk112344/proofdesk is PUBLIC.
  Unauthenticated metadata, README and MIT license access verified.
- GitHub protections: secret scanning, push protection and private vulnerability
  reporting enabled and verified.
- GitHub CI: [initial scaffold run](https://github.com/Jsjk112344/proofdesk/actions/runs/41681064090)
  passed on initialization commit fe195c1. Subsequent runs remain visible in Actions.
- Local scaffold: React/Vite screen and FastAPI health endpoint implemented.
- Observed local checks: locked dependency sync, Ruff lint/format, Python compilation,
  TypeScript/Vite build, API and built-page HTTP smoke checks, publication-file patterns
  and documentation links passed. Browser interaction and deployment remain unverified.
- Live research, model calls and generated-code execution: not implemented.
- Containment: not implemented or verified.
- Deployment resources: none provisioned by this project.
- Authorized cloud/model budget: none established; credits and inference coverage unverified.
- Public demo/video/slides: pending. Public code alone does not complete the entry.
- Submission: not submitted; no receipt.

## Open questions

Exact deadline/timezone and remote prize eligibility need organizer confirmation.
The public event date range does not establish an exact submission hour.
Before provisioning, confirm credit redemption, service coverage, resource pricing,
authorized spending cap and cleanup ownership. Do not publish account/billing details.

## Initial next implementation (superseded by the execution slice below)

Prove one bounded journey using permitted example inputs: sourced use case, demonstration
execution, artifact verification and saved draft. Establish runner containment before
allowing untrusted code. Select and evaluate Vultr models with an authorized call budget.

## Local execution slice: 2026-11-03

- Baseline inspected: `4bcbf91`, clean working tree. Work on `feat/local-execution-slice`.
- Implemented: CLI controller/runner interface, original labelled synthetic extraction,
  disposable Docker execution, fixed externally configured resource limits, pre-task
  kernel checks, strict artifact validation and atomic local execution records with
  documented JSON Schema. No HTTP execution endpoint, model or autonomous retry loop.
- Docker rechecked: client 29.6.2, server 29.5.2, Colima Linux/arm64, cgroup v2, seccomp.
  Official Python 3.12 slim Bookworm image explicitly pulled and digest pinned. No private
  images were reused; unrelated containers were left alone.
- Observed successful CLI probe pass: 15 labelled cases plus final valid fixture, every
  case matched its expected result and verified container removal. Example evidence IDs:
  `bda9f6c5cf2c4acb913072e3bae36dce` (wrong output, exit 0, rejected),
  `990d82f4334443a083d32b8eacd83e78` (deadline),
  `e44f58be38dd48eaad13bf76a0c30e38` (host canary),
  `4ed9daa3dffa46849e9818956c607bcb` (subsequent valid extraction).
  Full records are ignored under `.local/executions/<id>/record.json`.
- Actual resource behavior observed: memory allocation exited nonzero under the RAM cap;
  process creation hit EAGAIN; tmpfs writes hit ENOSPC; root writes failed. CPU quota was
  read from the kernel, not benchmarked. stdout and archive floods hit transport caps.
- Signal checks: SIGINT and SIGTERM produced interrupted records with verified removal;
  SIGKILL recovery removed the abandoned container and reconciled its pending record.
  A new valid task succeeded after each. Missing executable fault injection produced
  `docker_unavailable`, no task exit code or artifact, and explicitly unverified cleanup.
- Completed verification: all eight unittest groups passed with Docker enabled (including
  all live probe cases and three signal/crash cases). Offline run passed six groups and
  explicitly skipped two Docker groups. Locked sync, Ruff lint/format, compileall and
  TypeScript/Vite production build passed locally. Node was v26.5.0 here; CI remains pinned
  to Node 24. No remote CI run is claimed for this branch.
- Final live suite completed with all eight groups passing in 23.621 seconds, including
  a synthetic controller-secret sentinel and refusal to start work before crash recovery.
  Publication pattern/local-link checks passed for 46 tracked files; no labelled task
  containers remained after the suite. These checks do not constitute a full security audit.
- Initial runtime finding: Docker's copy API could not see `/work/out` on task tmpfs.
  Replaced collection with a bounded tar stream inside the task mount namespace. The
  host never extracts archive paths. Collection is not an atomic snapshot; only exactly
  validated bytes are accepted. Early failed attempts remain in local records.
- Initial signal harness readiness check omitted Docker's required PID column; corrected
  the test and reran it successfully. This was not a passed signal check before correction.
- Documentation now separates implemented local boundaries from future product criteria.
  Existing UI remains a health-check scaffold with updated status copy. CI adds offline
  behavior tests; live Docker tests remain opt-in. Added dev-only jsonschema and recorded
  dependencies/references in THIRD_PARTY.md.
- Commands run: `docker version`, `docker info`, explicit pinned image pull,
  `uv run python -m backend.app.execution run`,
  `uv run python -m backend.app.execution probe all`,
  `uv run python -m unittest discover -s backend/tests -v`,
  `PROOFDESK_DOCKER_TESTS=1 uv run python -m unittest discover -s backend/tests -v`,
  targeted signal recovery test, `uv sync --locked`, Ruff lint/format, Python compileall,
  `npm --prefix frontend ci`, TypeScript/Vite build and publication-file/link checks.
- Limitations: ordinary local Docker observations, no general escape guarantee; no Vultr
  runtime verification. Hard crashes/daemon outages require explicit recovery, with no
  independent watchdog service. Local records have no aggregate retention quota. Only
  synthetic inputs and a fixed extraction contract are supported. See SECURITY.md.
- Cloud/model spending: none; no credentials, account access or budget needed/used.
  Event and terms refreshed through the requested vultr-agent-rush skill; credits remain
  unverified. Nothing provisioned, pushed publicly or submitted in this session.
- Next step: under an explicit small spending cap and securely configured inference
  credential, connect one Vultr Serverless Inference model, generate a script, inspect
  an actual failure and make one bounded correction through this same controller.
  First add the corresponding provider, retry and spend accounting tests. Deployment,
  live research, outreach and hackathon readiness remain pending.

## Bounded generation and rejection fixes: 2026-11-03

- Resumed `feat/local-execution-slice` at `95b67b5`, clean working tree. No unrelated
  changes existed; existing fixture commands and the web health scaffold are preserved.
  Used the vultr-agent-rush skill for controller/containment/budget discipline. No new
  competition/market research or product research feature was added; only official
  provider technical references were checked (recorded in THIRD_PARTY.md).
- Fixed both reviewed rejection defects before model work: input/source bounds now
  precede content persistence/hashing, and pre-dispatch rejections never read reusable
  runner evidence or exit codes. Only bounded metadata is saved. Success → rejection →
  success with the same runner passes offline and in real Docker; successful task
  evidence identifies its own container. Record v2 documents null rejection hashes.
- Implemented controller-only Vultr HTTPS adapter with explicit model/deadline/token/
  response bounds, usage telemetry, strict protocol checks, no redirects, compression,
  SDK retries or provider fallback. A killable controller transport process enforces
  the total request deadline; it never executes returned code. No new dependencies.
- Implemented worst-case request/token/cost reservations, retained on errors/timeouts.
  Live requests require a key plus an exact owner-approved plan. Durable local approval
  ledgers prevent reloading a plan from resetting capacity; exhausted/corrupt ledgers
  stop. Current authorization remains **$0**; no live plan/key was required or used.
- Added `generate --provider fake|vultr`: source generation → existing Docker controller
  → exact validation → at most one eligible correction. Each generation and task has
  separate records linked by workflow/attempt and request/response/source hashes.
  Unsafe artifacts, policy/resource/infrastructure and cleanup failures stop immediately.
  Pending workflows/requests are abandoned on explicit recovery, without resend/refund.
- Added three synthetic evaluation cases (original, reordered EUR input, held-out Unicode/
  whitespace/three-item/zero-value input). Only the development document enters prompts;
  no expected answer enters generation or correction. An offline held-out-failure test
  inspects feedback and confirms document/answer withholding. These are public fixtures
  authored with the parser, not an independent model-quality benchmark.
- Provenance distinguishes `deterministic_synthetic_fixture`, `offline_provider_fixture`
  and future `vultr_model_generated` execution. Fake usage is explicitly synthetic;
  accepted response bytes and source are saved exactly. Malformed/oversized responses
  retain bounded sanitized metadata, no returned content. No offline pass is live evidence.
- Observed offline suite: 34 tests discovered, 30 passed and four Docker methods skipped
  explicitly (3.142 seconds). Covers missing key/approval, HTTP/transport errors, malformed/
  oversized responses, usage/token/request/cost limits, durable failed-call reservations,
  cleanup exceptions, terminal containment failures, held-out withholding and recovery.
- Observed final full Docker-enabled suite: all **34 tests passed** in **32.359 seconds**,
  including existing 15 probes, SIGINT/SIGTERM/SIGKILL recovery, rejection reuse, and new
  fake-provider Docker workflows (success, one correction, second failure stops). A final
  targeted recovery check also passed after ordering receipt recovery before workflow
  finalization, so interrupted recovery can be repeated. No paid requests occurred.
- Example ignored local workflow evidence from that full pass:
  `d978734133004f7fb793d7e5417395fe` — first incorrect output, one correction, all three
  cases passed; `232a644d4fc54d7686ecf313fa8d33f2` — two rejected script attempts, stopped.
  Earlier direct CLI `generate --provider fake --fake-outcome correct-once` also succeeded
  (`ea3bbc710e144294baa5c6e7b8b40556`). These scripts are canned fixture responses executed
  in Docker, not model-generated code.
- Actual CLI missing-credential check (key explicitly removed from environment) produced
  `missing_vultr_credentials`, zero reserved/sent requests and no task executions:
  `bcd80eecf2284a658548d9aa7ca8d612`. Its intended provider is labelled Vultr; it is not a
  live inference observation. Other provider failures were injected offline.
- Other completed checks: `uv sync --locked`, Ruff lint and formatting, Python compileall,
  `npm --prefix frontend ci`, TypeScript/Vite production build, and git whitespace checks.
  README, SECURITY, architecture, record v2/schema, acceptance, environment placeholders,
  contributor status and minimal screen status copy are aligned with implementation.
- Remaining limitations: no live Vultr request, selected model, verified price/billing,
  deployment or general escape guarantee. Input token admission uses a conservative byte
  estimate, requiring selected-tokenizer verification before live approval. Local ledgers
  are checkout-scoped and trusted, not account-wide billing controls; hard crashes still
  require explicit recovery. Local storage has no aggregate retention quota.
- Next authorized boundary: prepare the exact model/current pricing/tokenizer plan and
  conservative cap in docs/inference.md, then obtain only missing owner authorization
  before any paid call. No live spending, provisioning, outreach, publication, push or
  submission was performed in this continuation. No receipt or remote CI run is claimed.
- Final publication-pattern/local-link check passed for all 57 tracked files. No labelled
  ProofDesk task containers remained after verification. Only the intended implementation,
  tests, synthetic fixtures and documentation are included in the local commit.

## First-live preflight and authorization: 2026-11-03

- Resumed at requested commit `8413fcd` with a clean tree. Read contributor, architecture,
  inference and security instructions; used the vultr-agent-rush skill. No subagents,
  prospect research or Slack work were used.
- Refreshed official event/terms, Vultr model/pricing, completion limits and reasoning
  documentation. An actual public model metadata GET returned HTTP 200 for
  `qwen3.8-flash-next`, confirming $0.10/$0.20 per million input/output tokens and
  262,144-token context/output capacity. This metadata lookup is not inference.
- Owner explicitly approved `proofdesk-live-2026-11-03`: $0.02 total cap, at most two
  requests with one eligible correction, 60 seconds/request, 12,000 input and 4,096
  completion tokens/request, 32,192 reserved tokens total. Maximum token-priced API
  reservation is $0.0040384. Exact JSON is ignored at
  `.local/live-preflight/authorized-plan.json`; no ledger was reset or paid request sent.
- No inference credential was found in the process environment, project `.env`, or
  standard Vultr configuration locations. The owner's credential-location question is
  pending. No unrelated private repositories or correspondence were searched.
- Public upstream tokenizer/config/template are ignored local inspection materials.
  The initial request is 1,523 bytes; controller admission estimates 1,779 tokens;
  the inspected upstream default text template tokenizes to 360 tokens. Provider-side
  framing and usage still need an authorized live response. No template code executed.
- Observed offline tests: 34 discovered, 30 passed and four Docker tests skipped
  (3.685 seconds). Observed full local Docker suite: **all 34 passed in 40.360 seconds**.
  Docker server 29.5.2, Linux/arm64, cgroup v2/seccomp; pinned image present. Runner
  readiness passed after tests and no checkout-labelled task containers remained.
- Locked sync, Ruff lint/format, compileall, TypeScript/Vite build, and repository
  publication-pattern/local-link checks passed. Test log, catalog response/hash receipt,
  tokenizer/hash checks and readiness summary are ignored under `.local/live-preflight/`.
- Actual live generation/extraction remains **not attempted**, with $0 spent by this
  continuation. No live workflow ID, provider usage or model-quality result is claimed.
  The web journey is pending the requested live-generation prerequisite. Next action:
  use the owner's local credential location, run the exact approved plan through the
  existing sandbox/verification workflow, preserve the outcome, then build the minimal
  document-selection/run/progress/results journey if generation succeeds.

## First live requests, synthetic web journey and private Vultr deployment: 2026-11-05

- Selected challenge is now **Powering the Future of Work**, explicitly confirmed by the
  owner. Updated current contributor/README/architecture/submission guidance; historical
  Blast Radius Zero checkpoints remain dated. Refreshed official event/terms and current
  Vultr catalog/reasoning documentation. No registration, submission, public push or
  publication was performed. No prospect research or Slack work was added.
- Resumed commit `8413fcd`, preserving the three existing uncommitted documentation files.
  The console screenshot is unchanged and excluded via local `.git/info/exclude`; it was
  not opened, staged, committed or included in the release. Initial diff backup is ignored
  at `.local/live-preflight/continuation-start.patch`. No subagents were used.
- The ignored project `.env` provided the local inference credential. Checked only presence
  and model/endpoint match; no secret value was printed. Catalog GET on 2026-11-05 returned
  HTTP 200 and confirmed `qwen3.8-flash-next`, $0.10/$0.20 per million input/output tokens,
  context/output capacity and reasoning budget support. The Nov 3 approval file/identity
  was left intact; the Nov 5 metadata/receipt was saved separately.
- Actual initial workflow `985e8177be3b44828a04507c6e00d57e`: HTTP 200, 360 input + 4,096
  completion tokens, `provider_incomplete_response`. It stopped terminally with zero task
  executions and no automatic correction. Its full reservation was retained.
- The owner separately approved `proofdesk-followup-2026-11-05`: low reasoning effort,
  512-token reasoning cap, same original allowance/ledger, one request and no correction.
  Added bounded request-control loading/validation, receipt metadata and a one-attempt
  workflow restriction. A meaningful offline test verifies that controls cannot change
  the parent model/approval or restore the consumed ledger.
- Actual follow-up `6a7535b5c2714dfc948fc31d4b7e4fc0`: HTTP 200, 348 input + 1,091 completion
  tokens, `provider_malformed_response`. Zero task executions. Rejected content was not
  retained under the existing protocol contract; the exact invalid field/source defect
  is unknown. Do not infer Markdown fences or a model-name mismatch without evidence.
- The same ledger `95977722843a1e73f60b836ec4898f6400702edc8028f4bf4d15fb245736a8e6`
  records **2 requests, 32,192 tokens and $0.0040384 reserved**, under the $0.02 cap.
  Usage-priced estimate is $0.0011082 excluding unverified fees/tax/invoice rounding.
  No billing receipt/refund is claimed. **No request slots remain; no further paid call
  is authorized. Successful live-generated extraction remains unachieved.** Actual
  workflow/generation receipts and sanitized checkpoint stay ignored in `.local/`.
- Implemented minimal React journey: choose a synthetic document → start → saved progress
  → verified table/JSON, code and execution evidence → session history/reload. It clearly
  labels the original fixture parser and separately shows failed live provider checks.
  No fake live-generation success, fabricated progress percentage or automatic retry.
- Implemented fixed-input API, opaque HttpOnly/SameSite session capabilities, cross-session
  read refusal, same-origin/host checks, 2 KiB body limit, idempotency, one active run,
  five runs per anonymous session and twenty total by default, with durable local records.
  This is not enterprise account authentication. A trusted subprocess integrates the
  existing Docker controller and excludes inference keys from worker environments.
  Saved result hashes are checked before rendering; task text is escaped.
- Observed local checks: all **42 Docker-enabled tests passed**, covering existing probes/
  signal recovery and the new web worker/documents, ownership, quotas, duplicate requests,
  crash handling and artifact integrity. Offline suite: 37 passed, five Docker tests
  skipped explicitly. Local actual HTTP checks also executed all three documents with
  totals 1,600 / 408 / 2,195 cents and verified removal; web run IDs:
  `8cb77806cfcb443aa4c8e163755eb02d`, `f9fac6e95e804f74ab3feb61672eec1e`,
  `59e9adf33e4c4ccb9ec321804bac8c7e`.
- Owner-provided Vultr VM inspected over the existing SSH identity: Ubuntu 24.04, x86-64,
  4 GB class memory. Installed distribution Docker/Python venv tooling and pinned uv;
  no new VM, subscription, GPU, payment method or cloud resource was created. Existing
  VM billing and eventual VM teardown remain owner-managed. No credits were assumed.
- Private deployment installed at `/opt/proofdesk` with a hash-manifested allowlist bundle.
  Non-root `proofdesk` controller is a trusted Docker-group member. systemd service is
  active, bound only to `127.0.0.1:8000`; no public ingress/HTTPS was enabled. No inference
  key, approval or spending ledger was copied. Runtime: Docker 29.1.3, x86-64, cgroup v2,
  default seccomp/AppArmor; the pinned task image pulled successfully.
- Actual Vultr HTTP web runs succeeded for all three documents with exact totals and
  verified removal: `63542045d93b400ba71cf844e467fe9a` / task
  `0d4229124900407db36a5f8d1d95d96a`; `ba41aa7f8f9b4151b385d3d39e8e9489` / task
  `1e202748fa80430a8a6ac4d55a4c85dd`; `ce4d5d5d2b7f41199338ceb7e984b142` / task
  `8d5ef801b9354f3196068d31666a0453`. All are **deterministic fixture** execution.
  The 15 original fault probes plus final valid fixture also passed on this VM. No
  labelled task containers remained. Records stay on the VM and are copied locally
  under ignored `.local/deployment/`; this is narrow runtime evidence, not a general
  escape-protection guarantee.
- Browser interaction checks passed in a disposable network-disabled Playwright container
  against an explicitly mocked API: selection/start/progress/result, evidence/code tabs,
  reload history, mobile layout and no page errors. No browser ran on the host. PNG/JSON
  collection uses bounded tar reads without host extraction; container absence verified.
  Screenshots stay ignored in `.local/browser/`. An initial screenshot-copy attempt hit
  the already-known Docker tmpfs copy limitation; corrected collection and reran the
  browser check successfully. Mocked UI checks are separate from real HTTP/task evidence.
- Added dev-only HTTPX test dependency and documented licenses/references. No new app
  runtime dependency. Current checks also include locked sync, Ruff lint/format,
  compileall, TypeScript/Vite build, shell syntax and publication/local-link scanning.
- Next boundaries: inspect the private UI through SSH; successful model generation still
  requires a separately reviewed future plan, with no implicit budget reset. Public
  ingress/HTTPS and exact-content publication remain unapproved. Submission assets,
  public demo and receipt remain pending. Existing uncommitted work remains uncommitted.
- Final reviewed private bundle SHA-256:
  `7a9688341d3f923d7a8425d64eacc32e866bc4dbee06c8178d1c65b3d6ffa28d`.
  Server source hashes matched the manifest after installation. Final post-update web run
  `85054aab7ef3432fb74366f143d453d0` / task `afa9b547bde24deaac75c4b35ca38259`
  validated the Unicode fixture at 2,195 cents with verified cleanup. Its ignored receipt
  is `.local/deployment/final-server-check.json`.
- Final review added a recovery guard: a surviving worker cannot revive terminal work
  or publish a result after a new API process marks it abandoned. The focused seven-test
  web suite, including real Docker execution, passed after that change; the complete
  42-test Docker suite passed before it. Final formatted browser build and interaction
  checks also passed. All 66 intended worktree files passed bounded publication-pattern/
  local-link scans; shell syntax, Ruff, compileall and whitespace checks passed. The
  temporary local verification server was stopped; the private Vultr service remains active.

## Sales agent reorientation, model-integration fix and redeployment: 2026-11-05 (second continuation)

- Resumed `8413fcd` with the earlier uncommitted web/deployment work intact and preserved.
  Verified the VM facts over SSH before changes (host `proofdesk-web`, Ubuntu 24.04 x86-64,
  service active as `proofdesk`, API on `127.0.0.1:8000`, `/opt/proofdesk`, Docker 29.1.3,
  5 web runs and 22 execution records present, no labelled containers). Used the
  vultr-agent-rush skill's challenge/deployment/budget discipline and the impeccable skill's
  product-register guidance; no Ducket code, data or tokens were used. No subagents.
- Refreshed the event page (now served from lablab.build): Future of Work requires a Vultr
  VM backend, web app, public repo, demo URL and video; **Serverless Inference and
  sandboxing are optional** and remain ProofDesk's own choices. Refreshed the official
  chat-completion contract, reasoning and limits docs and the public model catalog (free
  GET, receipt `.local/live-preflight/catalog-receipt-2026-11-05-session2.json`:
  `qwen3.8-flash-next`, $0.10/$0.20 per million tokens, `response_format` and
  `reasoning.max_tokens` supported). No paid request was made in this continuation.
- Reoriented the product: new `backend/app/sales/` package (SSRF-protected retrieval,
  verbatim evidence and controller demonstration rule, separate research/outreach/source
  contracts with sanitized diagnostics, controller-owned drafting with footnotes, prospect
  store with ownership/idempotency/quotas/draft versions/review, agent orchestration),
  `sales_worker.py` subprocess, `python -m backend.app.sales` CLI, new `/api/prospects`
  endpoints (create, list, detail, draft edit, review) and a rewritten React workspace
  (landing form, Research/Demonstration/Outreach views, secondary Technical details). The
  extraction endpoints remain as the demonstration capability only. Three synthetic
  prospect sites were authored under `fixtures/prospects/`.
- Model integration: `generation/provider.py` now shares transport, usage accounting and
  ledgers across contracts through `complete()`; receipts are schema v2 with `contract`,
  `request_options`, `response_model`/`model_echo_matches`, `finish_reason`,
  reasoning presence/chars/tokens, `content_chars`, `content_head` and a field-level
  `diagnostic` on rejection; rejected content is never stored. Documented compatibility
  changes: the response `model` echo is recorded instead of rejected (official contract:
  "may differ from request"), `reasoning: {"enabled": false}` and
  `response_format: {"type": "json_object"}` are supported request options, plans may hold
  up to six requests. Fences, tool calls, non-`stop` finishes, missing usage and oversize
  bodies still fail closed. A `ReplayProvider` serves saved accepted responses for
  byte-identical requests. **The second live failure's root cause remains unknown**; the
  model-echo rule is a documented possibility, not an established cause.
- Live-validation plan prepared (unapproved, `approval_reference` empty) at
  `.local/live-preflight/proposed-sales-plan-2026-11-05.json`: `qwen3.8-flash-next`, 60 s
  deadline, 16,000 input / 2,048 completion tokens, reasoning disabled, at most four
  requests (research, outreach, code generation, one eligible correction), no retries,
  worst case 72,192 tokens / **$0.0080384**, requested ceiling **$0.01**, new ledger
  identity. Zero live requests were sent; the exhausted ledger was not touched.
- Observed offline suite: **67 tests passed**, 5 Docker tests skipped. Covers URL/address
  policy (loopback, private, link-local, mapped, ULA, mixed answers, redirect to metadata,
  redirect loops), size/type/encoding/page caps, fixture sites, evidence rules, contract
  acceptance and rejections (unknown source, excerpt not in source, unknown claim id, key
  mismatch, unsupported numbers/savings words, named greeting, demo mention without
  verification), reproduced live failure shapes with field-level diagnostics, journeys
  (relevant, failed demo, irrelevant, sparse, blocked fetch, hostile page, live mode with
  fixture responses and a fabricated-citation stop, live mode without plan), ownership,
  quotas, idempotency, edits/review, recovery and API behaviour.
- Observed full Docker suite: **all 67 tests passed in 41.510 s** (log
  `.local/live-preflight/docker-tests-2026-11-05-session2.log`), including the 15 probes,
  signal/crash recovery, web worker documents and generated-response fixtures; no labelled
  containers remained. Lint/format, compileall, TypeScript/Vite build and the publication/
  link scan (84 worktree files) passed.
- Observed CLI journeys with real local Docker: `f2d2c63bf0744427b718af9799d7e921` (synthetic
  3PL: 4 pages, 6 verbatim claims, demonstration verified), `310274a8f4964e2bac26659efc9527d3`
  (synthetic bakery: skipped as irrelevant), `f4084526c5b34f84b2f2b2538766c2fe` (synthetic
  placeholder: insufficient evidence).
- Observed actual local HTTP journey (`.local/live-preflight/local-web-http-2026-11-05-session2.json`):
  policy rejections over the API, idempotent duplicate, refusal while active, sample
  prospect `ee7edb5d889f4bb49cf9deda667f9805` with demonstration execution
  `319e6dba76cd49b9a501d33384482c15` (exit 0, 1,600 cents, cleanup verified), review of v1,
  edit to v2 resetting review, stale review refused, **real retrieval of
  `https://example.com/`** (prospect `4e3d454636404b4ba839205fde85bd72`, insufficient
  evidence, honest draft), cross-session 404s and reload history.
- Observed mocked-UI browser check in the disposable network-disabled container: 10 checks
  passed (landing asks for offering/website, blocked-address message, research brief,
  demonstration, review/edit, reload, skipped demonstration, model-validation failure
  diagnostic, mobile layout, no page errors). Screenshots under `.local/browser/`.
- Redeployed the private release (bundle SHA-256
  `0806010ef9fbf0eeda7b735b0c87b8cf7a2a5b9d27dd127d825a871f8a16a0e5`, 52 allowlisted files,
  no credentials/records/screenshots) after snapshotting the previous install to
  `/opt/proofdesk-rollback/proofdesk-20261105T200643Z.tar.gz` (excludes `.local`). Service
  restarted and active on loopback only; all 52 manifest hashes matched; prior records
  preserved (5 web runs, 22 executions). No ingress, credential, plan or ledger deployed.
- Observed actual Vultr HTTP journey on the VM (`.local/deployment/vultr-sales-check-2026-11-05.json`):
  policy rejections, idempotent duplicate, sample prospect `56e1dba371704e9d9517a099dc1e3753`
  with demonstration execution `2d981ba27b3348d5aa95eb3f8c74bc83` on the VM (exit 0,
  1,600 cents, cleanup verified), review/edit/stale-review behaviour, real retrieval of
  `https://example.com/` from the VM (prospect `469323cd9c254dd5a6fbcde81cd7d62f`,
  insufficient evidence), cross-session 404 and reload history. Copies of those records are
  under ignored `.local/deployment/vultr-prospects/` and `vultr-executions/`.
- Not done: `.env.example` could not be updated because the session's permission policy
  denies every tool call touching `.env` paths; the new variables
  (`PROOFDESK_SALES_LIVE_PLAN`, `PROOFDESK_PROSPECT_STORE`, `PROOFDESK_WEB_MAX_PROSPECTS`)
  are documented in README and infra docs instead. Nothing was committed, pushed,
  published or submitted. Successful live inference, public demo, video and submission
  remain pending; those criteria are reported as incomplete.
- Next concrete action: Phase 1 of [docs/plan.md](docs/plan.md) (failure-story README,
  invariants-to-evidence table with a drift checker; no budget needed), then owner approval
  of the proposed live-validation plan for Phase 2: one authorized run of
  `python -m backend.app.sales run --sample harbor-vale-freight --provider vultr
  --authorization <plan>` plus the code-generation workflow, preserving receipts and
  reporting the sanitized diagnostics if any contract rejects the response. Phases 3 to 5
  (honest measurement, public evidence page, submission assets) and their authorizations
  are defined in the plan.

## SalesDesk rename and forward-plan correction: 2026-11-05

- Owner renamed the product to SalesDesk and requested the revised forward plan. Updated
  app navigation, page metadata, API title/health identity, exported draft filenames and
  copy, research user-agent, package metadata/locks, fixture branding and current docs.
- Kept the checkout path, Vultr hostname/resources, `proofdesk` service/user/install path,
  `PROOFDESK_*` configuration, session cookie/header, execution labels and historical
  approval/record identifiers intact for compatibility. Existing dated history is preserved.
- GitHub repository is now public at https://github.com/Jsjk112344/salesdesk. Updated origin
  and current links. A separate clean worktree published only a branding change on main,
  commit `52330e0`; it did not publish the uncommitted sales implementation. Reconcile that
  branding commit when eventually integrating `feat/local-execution-slice`; never reset
  the existing working tree to main. The temporary branding worktree was removed afterward.
- Revised docs/plan.md: correct overstated guarantees, complete one useful live sales
  journey, prepare the public product alongside it, evaluate factual support and draft
  usefulness separately, then finalize submission assets. Generated code is optional for
  the first live sales milestone; a rejected request leaves that milestone incomplete.
- The preceding review reproduced two contract gaps without paid calls: an unrelated
  lunar-warehouse claim paired with a genuine freight quote passed research validation;
  an unsupported 42-warehouse statement passed outreach validation. These remain unfixed
  implementation work for the next session. Existing tests passing does not resolve them.
- Observed rename checks: locked dependency sync, Ruff lint/format, frontend production
  build, publication/local-link check and all 67 Docker-enabled backend tests passed.
  Disposable browser sales-journey checks passed with mocked API and SalesDesk copy;
  container removal verified. No live inference or new paid resource was used.
- Updated existing private Vultr deployment with an allowlisted bundle, SHA-256
  `5b42caa1cc537d005503ce5699a37299249563ea0563c8039588a37ff81c6d70`.
  Verified all 52 manifest hashes, HTML title, served JS branding and health service
  `salesdesk`; mode remains `deterministic`. All 29 existing prospect/execution/web records
  were unchanged. No public ingress, credential or budget ledger was added.
- Rollback snapshot: `/opt/proofdesk-rollback/before-salesdesk-20261105T202746Z.tar.gz`.
  Live verification receipt: `/root/salesdesk-brand-verification.json` on the VM.
- This checkpoint supersedes the previous "failure-story README and drift checker" next
  action. Next session implements Phase 1's contract corrections with positive/negative
  regression tests, prepares one concrete bounded live-debug/evaluation authorization,
  and pursues Phase 2 success once approved. No new spending authorization was granted.
- Remote CI for the isolated public branding commit passed:
  https://github.com/Jsjk112344/salesdesk/actions/runs/42103778400.
  The existing local tunnel also returned `service: salesdesk` from `/api/health`.

## Phase 1 contract corrections, envelope ledger and public-demo preparation: 2026-11-05 (third continuation)

- Resumed the uncommitted SalesDesk working tree on `feat/local-execution-slice` (HEAD
  `8413fcd`) and preserved it. Read the contributor, plan, status, README, security,
  inference, architecture and contributing documents and the vultr-agent-rush skill. No
  subagents, Slack, CRM or external services were used. The public branding commit
  `52330e0` on main was inspected (13 files, STATUS.md conflicts against HEAD) and is
  reconciled by merge below; the working tree was never reset.
- **Both reproduced defects were turned into failing regression tests first, then fixed.**
  (1) "They operate a warehouse on the Moon." attached to a genuine freight excerpt now
  fails the research contract with field `claims[0].text`, observed
  `interpretation_not_grounded`: a claim's text may only recombine words and numbers from
  its own verified quotation (light stemming, company name allowed). (2) "Your team operates
  42 warehouses" now fails the outreach contract with `unsupported_quantity`
  (`numeral`, `no_matching_number`); written numbers, quantifiers, percentages and
  currency amounts are covered, and a genuine number reused for a different subject
  ("fleet of 38 warehouses", "300 invoices", "24,000 pallets", "2009 pallets") fails with
  `number_in_other_context`. Supported counterparts pass ("a fleet of 38 vehicles", "more
  than 300 suppliers", "since 2009 … two bonded warehouses", the verified demonstration's
  figures). Quantities are also refused in the brief's summary, hypothesis, unknowns and
  relevance reason. Outreach numbers must come from claims the paragraph cites.
- Representation: quotations carry `verification: verbatim_quotation`; interpretations
  carry `text_kind` (`verbatim`, `grounded_restatement`, `model_summary`). The UI shows
  the quotation as the fact and labels restatements and model summaries as not verified.
  Prompts tell the model the same rules. These are lexical/attributional checks; README,
  SECURITY, architecture, inference and the UI now say so (mechanism/evidence/limitation
  table in README) and no longer claim byte-exact artifact comparison (it is canonical
  JSON values), universal factual accuracy or sandbox escape protection.
- Implemented an optional aggregate **envelope** in plan files with its own durable,
  file-locked ledger that every batch reserves against first, so batched plans cannot
  exceed the owner's total and a plan with changed model settings reopens the same
  aggregate. Exhaustion stops before dispatch (`model_envelope_exhausted`); tampering
  stops (`model_envelope_ledger_invalid`); nothing refunds. Covered by
  `test_envelope_aggregates_batches_and_never_resets`. The exhausted 2026-11-05 ledger
  was not touched.
- Prepared the consolidated authorization proposal (docs/inference.md and ignored
  `.local/live-preflight/proposed-live-envelope-2026-11-05.json` plus four batch plan
  files): `qwen3.8-flash-next`, rates re-read today ($0.10/$0.20 per million tokens,
  receipt byte-identical to the earlier one), per request 16,000/2,048 tokens and 60 s,
  worst case $0.0020096; batch 1 live debugging ≤ 6 requests ($0.015); batches 2–4
  evaluation 16 requests; envelope 22 requests / 397,056 tokens / worst case $0.0442112,
  requested ceiling **$0.05**; no retries; permitted adjustments listed. **Not approved;
  no live request was sent; $0 model usage this continuation.** The key in the ignored
  `.env` was only checked for presence.
- Implemented public-demo mode (`PROOFDESK_PUBLIC_DEMO=1`): synthetic scenarios only unless
  a host is allowlisted, three prospects per session, bounded total (100 default, 200 cap),
  truthful `public_demo` flag in API and UI, live mode refused without `PROOFDESK_PUBLIC_LIVE=1`.
  Prepared `infra/Caddyfile.public` and `infra/proofdesk-public.conf` (inert templates in
  the bundle) and the activation proposal `docs/public-demo.md`. **Not activated**; the
  hostname and approval are requested there.
- Observed checks: offline suite **71 tests passed**, 5 Docker methods skipped (4.8 s);
  Docker-enabled suite **all 71 passed in 46.8 s**, no labelled containers remained (log
  `.local/live-preflight/docker-tests-2026-11-05-session3.log`); Ruff lint/format,
  compileall, TypeScript/Vite build and the publication/link scan (88 worktree files)
  passed; disposable browser check **11 interactions passed** including the new public-mode
  pass (`.local/browser/browser-check.json`). Local rule-based CLI journey with real Docker:
  prospect `6f242e07e5cf40ff810a421f75813b1a`, 6 verbatim claims, demonstration verified.
- Updated the private Vultr deployment: bundle SHA-256
  `58cb4de2b299ef8e7ab8e24ab3dd332febc61083ed7ff16baf0e465128b5f187` (54 allowlisted files,
  no credentials or records); rollback snapshot
  `/opt/proofdesk-rollback/before-phase1-20261105T211841Z.tar.gz`; all 54 manifest hashes
  matched; service active on loopback, `public_demo: false`; existing records preserved
  (2 prospects / 23 executions / 5 web runs before and after the update). Observed VM HTTP
  journey afterwards: prospect `34bc4c057d5e47578019df31f74268e2`, rule-based, 6 claims with
  the new labels, demonstration execution `bdf6885e2cd84326898a6d175e6ba835` verified (exit
  0, 1,600 cents, cleanup verified), cross-session 404, no containers left (copy at
  `.local/deployment/vultr-phase1-journey-2026-11-05.json`).
- Tool rejection: the session's permission policy denied the write to `.env.example`
  (reads of variable names worked); the new variables are documented in README and
  infra/README instead.
- Evidence kinds this checkpoint: **rule-based** (local CLI and VM HTTP journeys, real
  Docker), **offline fixture** (contract, envelope, public-mode and journey tests), **mocked
  UI** (browser). **No live model output and no replay output exist for the sales
  contracts.** Executor review only; no human seller feedback was collected.
- Next concrete action: owner approval of the consolidated envelope (write the approval
  reference into the envelope block and batch 1), then one authorized run of
  `uv run --env-file .env python -m backend.app.sales run --sample harbor-vale-freight
  --provider vultr --authorization .local/live-preflight/proposed-batch-1-live-debug-2026-11-05.json`,
  preserving receipts and reviewing factual support, specificity, demonstration relevance
  and draft usefulness. A rejected response is diagnostic progress, not completion. In
  parallel, the owner's hostname decision and approval of docs/public-demo.md unblock
  public activation.

## Historical campaign experiment, durable jobs and private Vultr verification: 2026-11-05 (fourth continuation)

- Resumed `ee64b08` with the untracked `docs/session-prompts/` preserved. The owner's expanded
  direction (evidence, statistics and AI reasoning → approved next actions → scheduled work →
  measured results, with Slack/HubSpot and all integrations deferred) is recorded in AGENTS.md
  and docs/plan.md. No subagents; no Ducket code or data; the vultr-agent-rush skill's
  challenge/deployment/budget discipline was followed.
- **Data.** The pinned Hillstrom file (3,964,977 bytes, SHA-256 `0e5893…1aece`) imported with
  64,000 rows and exactly the documented arms (Mens 21,307 / 3,894 / 267 / $30,311.69; Womens
  21,387 / 3,238 / 189 / $23,038.11; No E-Mail 21,306 / 2,262 / 122 / $13,908.33) locally and
  on the VM; equal-valued rows keep their multiplicity (57,438 distinct lines, maximum 31).
  Checksum, size, header, arm, non-finite/negative/over-precise spend, non-binary and missing
  values are rejected visibly (offline tests). Rights boundary recorded in THIRD_PARTY.md.
- **Computation.** `backend/app/experiments/analysis_program.py` (`salesdesk-analysis-1`, 9.4 KB)
  runs in the sandbox with a 30 s wall clock and 1 MiB typed input (controller extension with a
  result validator; schema updated). Hillstrom result: purchase rate 1.25% (267/21,307) vs 0.57%
  (122/21,306), difference +0.68 pp (Newcombe 95% CI +0.50 to +0.86), visits +7.66 pp (+7.00 to
  +8.32), incremental spend +$0.77 per assigned customer (seeded 2,000-resample bootstrap 95% CI
  +$0.49 to +$1.06). Reconciliation against the importer's Decimal aggregates and the
  controller's Wilson/Newcombe matched. Newcombe's six published Table II intervals and a
  bisection cross-check of Wilson pass offline. Artifact SHA-256
  `3b3152bfdf0d6cd72552d3a0cb3d1bd5e5220a8001eef68c69a944b1ea519469` was reproduced by two local
  runs and two VM runs (same pinned image).
- **Interpretation.** Rule-based reading (labelled, passes the same analysis contract); live mode
  reuses the provider transport and ledgers; the contract refuses raw numbers, ROI wording,
  unknown metric ids and actions against the historical records; a failed live step preserves
  the statistical result (offline tests with fixture responses, including budget exhaustion).
  **Live AI status: not demonstrated.** Zero live requests were sent; $0 model usage.
- **Tasks and jobs.** SQLite store under `.local/experiments/` with unique operation keys,
  lease-claimed jobs (`analyze_plan`, `prepare_packet`), bounded single requeue, unique
  artifacts per job, approval bound to proposal/artifact/plan hashes, invalidation on edit,
  stale approval refused by the worker, packet assembly without a model call, readiness checks
  separating entered inputs from external prerequisites.
- **Observed local evidence.** Offline suite **93 tests passed** (6 Docker methods skipped);
  Docker-enabled suite **93 passed in 41.6 s** (log `.local/live-preflight/docker-tests-2026-11-05-session4.log`,
  rerun after the recovery fix `…session4b.log`, no labelled containers remained); Ruff
  lint/format, compileall, TypeScript/Vite build, publication/link scan passed; browser check
  **18 interactions passed** (experiment overview → plan → results → interpretation → next
  action → packet → queue, prospect journey, public mode, mobile; `.local/browser/`). Real
  local HTTP journey with real Docker and a controlled API restart during the analysis job
  (`.local/live-preflight/local-experiment-http-2026-11-05.json`): job requeued
  (`interrupted_requeued`), attempt 2 succeeded, single artifact, packet prepared after a 15 s
  absence, cross-session 404s.
- **Private Vultr deployment.** Bundle `4b11b686…b92b` (66 files, no dataset, no secrets)
  deployed after snapshot `/opt/proofdesk-rollback/before-experiments-20261106T001348Z.tar.gz`;
  dataset copied by scp to `.local/data-research/hillstrom/` (0600, owner `proofdesk`) and
  imported as the service user; all 66 manifest hashes matched; prior records preserved (3
  prospects / 24 executions / 5 web runs). The first VM journey exposed a restart race: SIGTERM
  during `docker create` left a "Created" container and the job failed `cleanup_unverified`
  (preserved as job `61d439f3…`). Fix: bounded repeated removal in `DockerRunner.cleanup`,
  interruption takes precedence over the cleanup check, and the API runs the existing sandbox
  recovery at startup. Redeployed bundle `847be36d…be9b` after snapshot
  `before-experiments-fix-20261106T001755Z.tar.gz`; startup recovery removed
  `proofdesk-72987a42…` and reconciled its record (`last_recovery` in the overview).
- **Observed VM journey** (`.local/deployment/vultr-experiment-journey-2026-11-05.json`, through
  an SSH tunnel on 18001; port 18000 is held by a stale tunnel from an earlier session): plan
  `84445f7f…`, analysis job `d467a214…` interrupted by `systemctl restart proofdesk` at
  00:18:18 UTC, requeued and completed on attempt 2 (execution `213702c0…`, cleanup verified),
  identical artifact hash on the second run, proposal v2, task approved (old version refused),
  packet job `6ada9af0…` due 20 s later ran with the client absent, packet
  `212e1e60…` downloadable (10,759 bytes Markdown), task completed, cross-session 404s. VM
  state afterwards: 2 plans, jobs {failed 1, succeeded 3}, tasks {completed 1}, 28 executions,
  0 labelled containers, service active on loopback only, no public ports.
- **Public access.** Public-demo mode extends to experiments (3 plans / 6 runs / 6 tasks /
  3 queued jobs per session, 24-hour due horizon, 200 jobs total, no live mode), tested
  offline and in the browser check. Not activated: the hostname decision and approval of
  docs/public-demo.md remain the exact gap; no ingress, Caddy, DNS or certificate exists.
- Tool rejection: `.env.example` remains untouched by policy; variables are documented in
  README. Nothing was committed, pushed, published or submitted. Video and submission assets
  are pending (walkthrough drafted in docs/demo-walkthrough.md).
- Next concrete actions: (1) owner approval of batch A in
  `.local/live-preflight/proposed-analysis-envelope-2026-11-05.json`, then one local and one VM
  run with `PROOFDESK_ANALYSIS_LIVE_PLAN`; (2) hostname decision and approval of
  docs/public-demo.md for public activation; (3) commit the reviewed working tree on
  `feat/local-execution-slice` and plan the public push; (4) record the video.

## Hackathon phase 2 activation attempt

- Existing VM is in EWR (New Jersey), hostname proofdesk-web, instance metadata id
  113716844. No new VM provisioned. Caddy installed; public-demo and live plans configured
  through root-owned systemd configuration; credentials excluded from release and logs.
- Selected hostname: salesdesk.149.28.51.139.sslip.io, DNS resolves to the existing VM.
- Host firewall permits TCP 80/443, Caddy listens on both, API stays on loopback.
- External connections still time out and ACME validation reports connection timeout.
  Public HTTPS is NOT verified. Owner asked to open the upstream Vultr firewall or locate
  management credentials; only the inference key is configured locally.
- Public URL is pending external ingress, not ready for judges. Subsequent UI work may
  proceed while the external firewall is corrected; activation acceptance remains open.
