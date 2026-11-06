# SalesDesk: two doors, one analyst loop

SalesDesk has two entry doors: **See what worked** for campaign analysis and
**Starting from zero** for prospect research. Both lead to an evidenced next move,
human approval and work prepared by Vultr workers while the user is away.

The campaign opens with a compact activity stepper and an answer card: the analyst's
headline, two purchase rates and one approval/download slot. A purchase-rate chart remains
visible; See full analysis retains the complete reading, uncertainty, metrics, secondary
outcomes and spend. Next move defaults to a five-line read-only summary; Edit reveals the
existing form and Advanced holds scenario/sample-size inputs. The approval/download slot
uses the existing task operations and saved packet records.

Activity expands while jobs are active or when clicked, then collapses after completion.
Default steps show labelled dots; timestamps and completion detail are disclosed on demand.
Hash/version/metric references and raw activity evidence live under one Verification entry.
Prospects open on the draft, with a short excerpt, an exact-version Approve draft action,
Read & edit draft, collapsed sources, and the existing Research/Demonstration tabs.
Home keeps its hero, two entry doors and stats; its single Verification link opens source
context in a dialog. The sidebar keeps navigation and saved analyses.

Approve & schedule invokes the existing idempotent create-task, exact-version approval
and schedule endpoints in order. Request ids persist through a retried click; editing
resets them. Each server operation retains its ownership, quota and version checks;
a partial network failure keeps the saved task for recovery. Packet status and Markdown
download remain in the answer card across reloads. The browser polls active jobs; the
server scheduler owns execution.

Live Vultr analysis, research and outreach have passed their unchanged validators.
Public workers prefer exact-input accepted replay, revalidate it and label provenance.
No model/provider fallback is silently substituted. Caddy public ingress is configured;
external HTTPS acceptance is tracked separately in STATUS.md.

The sections below record the underlying components and retained contracts.

## Components

**React workspace** (`frontend/src/`): `main.tsx` is the shell with hash routes (`#/`
overview, `#/experiments/new`, `#/experiments/<id>`, `#/queue`, `#/prospects`);
`experiments.tsx` holds the overview, plan form, experiment detail (Results, Interpretation,
Next move, Scheduled work, Plan and source, Verification) and the action queue;
`prospects.tsx` is the Starting from zero moved mostly verbatim. Charts are inline SVG with
denominators, interval methods and artifact provenance in their captions.

**API** (`backend/app/main.py`): anonymous HttpOnly/SameSite session capabilities,
same-origin JSON checks, bounded bodies, idempotent writes by request id, cross-session 404s.
Experiment endpoints under `/api/experiments` (datasets, plans, runs, proposals, tasks, approve,
schedule, cancel, complete, jobs, artifacts, packet download); prospect and extraction endpoints
unchanged. The lifespan starts the scheduler thread; one Uvicorn worker.

**Experiment store** (`backend/app/experiments/store.py`): versioned SQLite under ignored
`.local/experiments/` with datasets, plans and plan versions, jobs, runs, artifacts, proposals,
tasks and operation keys. Parameterized SQL, `BEGIN IMMEDIATE` transactions, WAL, owner hashes
on every row, unique operation keys per request, unique artifact per job. Prospect JSON stores
and execution records are untouched.

**Ingestion** (`experiments/ingestion.py`): pinned source definition, bounded checksum-verified
fetch, strict typed importer, manifest with aggregates and limitations, typed analysis input.
See [experiments.md](experiments.md).

**Analysis program** (`experiments/analysis_program.py`): fixed, versioned, standard-library
script executed only inside the sandbox; Wilson, Newcombe, seeded customer-level bootstrap,
descriptive exploratory cells; deterministic output.

**Contracts** (`experiments/contracts.py`): plan validation (original arms only), the
analysis-result contract with reconciliation against the importer and the controller's own
statistics, metric derivation and formatting, the model analysis contract (placeholders only,
no raw numbers, no ROI wording, no action against the historical records), proposal and task
validation, task and job state machines.

**Reasoning** (`experiments/reasoning.py`): the rule-based reading, prompts, and the live step
through the shared provider transport with its budget ledgers and receipts. The model sees
metrics and limitations only.

**Jobs** (`experiments/jobs.py`, `worker.py`): `Scheduler` (API thread; reconcile lost workers,
claim one due job under a lease, launch a worker subprocess with an allowlisted environment)
and `run_job` (analysis or packet assembly, lease re-validated before every write, bounded
requeue after interruption or lost lease, failure recorded). `execution/controller.py` gained a
narrow extension: an optional result validator with its label, a 1 MiB typed-input cap for the
analysis profile and a 30 s wall clock; scripts stay capped at 32 KiB and the container policy is
unchanged.

**Packet** (`experiments/packet.py`): assembly from the artifact, accepted interpretation,
approved proposal, task and dataset provenance; readiness checks; scenario and sample size only
from entered inputs; Markdown rendering; no model call.

**Service** (`experiments/service.py`): owner-scoped operations, quotas (private and public),
approval binding, invalidation on edit, due-time horizon, views.

**Prospect workspace** (`backend/app/sales/`, `web_jobs.py`, `web_worker.py`): unchanged;
see the component descriptions in git history and [inference.md](inference.md).

## Trust boundaries

- The controller (API, scheduler, workers, CLI) owns policy, quotas, budgets, credentials,
  records and state. Models propose through validated contracts; deterministic code decides
  what executes. A model cannot change source rows, methods, confidence levels, allocation,
  task approval or job destinations.
- Only the fixed analysis program and the typed derivative enter the analysis sandbox; the
  raw CSV never leaves ignored storage. The worker receives the inference credential only when
  live mode is configured; Docker sandboxes never do.
- Every number shown comes from a validated artifact or an explicitly labelled entered
  assumption. Approval binds to hashes; editing invalidates; the worker re-checks before
  assembling. Jobs survive restarts through leases, bounded requeue and unique artifacts.
- Anonymous sessions isolate plans, runs, tasks, jobs and artifacts; public demo mode adds
  smaller quotas and a shorter due horizon and uses configured live mode with accepted exact-input replay.

## Deployment

The existing Ubuntu Vultr VM in EWR hosts the API, scheduler, SQLite store and Docker
workers under a non-root service user. Caddy serves public HTTPS at
salesdesk.149.28.51.139.sslip.io and proxies to loopback. Inference credentials and bounded
operator plans are deployed outside the release archive. Live contracts passed; identical
public inputs replay accepted responses. See infra/README.md and STATUS.md for evidence.

## Out of scope

No CRM, Slack, mailbox connection, bulk lead discovery, autonomous sending, browser automation,
paid search, new cloud services, GPU dependency, uplift models, bandits, automatic targeting,
arbitrary agent code execution or generic agent framework. One dataset, one fixed analysis
program and two job kinds exist.

## Seeded public examples

The browser initializes a public session through same-origin POST `/api/demo/seed` before
showing the dashboard. Repeated calls use stable operation keys with the existing services:
one plan, one Docker analysis job, one example task/approval/packet job and one prospect.
The normal scheduler and prospect worker do the work; the endpoint polls saved progress
and never runs a host analysis. Accepted identical model responses replay through validation.
One example consumes one plan, run, task, prospect and two jobs from that session's normal
quotas; no limits are reset or bypassed. New analysis plans and prospects remain available.

The seeded approval is labelled as a demo example. Reload never approves visitor changes,
revives cancelled work, launches a campaign or sends the prospect draft. Session ownership
applies to every generated record and packet. Private mode cannot invoke initialization.
