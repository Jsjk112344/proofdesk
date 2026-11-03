# Project status

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
