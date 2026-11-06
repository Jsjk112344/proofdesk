# SalesDesk: two doors, one analyst loop

SalesDesk has two entry doors: **See what worked** for campaign analysis and
**Starting from zero** for prospect research. Both lead to an evidenced next move,
human approval and work prepared by Vultr workers while the user is away.

The campaign page has three tabs: Result (interpretation and charts), Next move
(editable content, schedule and one approval card), Verification (source, saved plan,
execution, reconciliation, model receipts and job history). Analyst activity is derived
from persisted job events, execution records and generation receipts. Pending work is
never marked complete before evidence exists. Per-step evidence is disclosed on demand.
The same timeline component shows prospect research, brief, demonstration decision,
draft and approval readiness.

Approve & schedule invokes the existing idempotent create-task, exact-version approval
and schedule endpoints in order. Request ids persist through a retried click; editing
resets them. Each server operation retains its ownership, quota and version checks;
a partial network failure keeps the saved task for recovery. Packet status and Markdown
download remain visible across tabs and reloads. The browser polls active jobs; the
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
  smaller quotas and a shorter due horizon and keeps live mode off.

## Deployment

A single Ubuntu VM on Vultr runs the API with its scheduler thread, workers, the SQLite store
and the Docker daemon under a non-root controller user, bound to loopback; access is through an
SSH tunnel. The dataset is placed on the VM outside the bundle. No public ingress, HTTPS, domain
or inference credential is deployed. See [infra/README.md](../infra/README.md) and
[public-demo.md](public-demo.md).

## Out of scope

No CRM, Slack, mailbox connection, bulk lead discovery, autonomous sending, browser automation,
paid search, new cloud services, GPU dependency, uplift models, bandits, automatic targeting,
arbitrary agent code execution or generic agent framework. One dataset, one fixed analysis
program and two job kinds exist.
