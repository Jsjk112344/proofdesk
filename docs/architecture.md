# Architecture and first workflow

The full product architecture below remains planned. The health endpoint, bootstrap
screen and a separate bounded generation/execution CLI exist today. Live model requests
have not been verified.

## Implemented execution slice

`python -m backend.app.execution` selects an original synthetic fixture or labelled probe.
`controller.py` owns the fixed limits, expected output, serial lock, hashes, validation,
atomic JSON records and cleanup. `Runner` accepts immutable script/input bytes and limits;
the Docker implementation returns exit status, bounded logs, an untrusted archive and
pre-task policy evidence. This interface does not authorize execution by a model.

The runner creates a fresh container, checks Docker policy and actual kernel limits,
then streams input/code through stdin to an isolated Python process. Only Docker client
commands run on the host; task Python never does. A trusted pinned image supplies Python
and tar. Artifact collection uses a bounded tar stream inside the task mount namespace
because this local daemon's copy API could not read task tmpfs. Host validation reads the
archive without extracting it and saves only exactly validated bytes at a fixed filename.
The finalizer removes the whole container on success, failure, timeout or interruption.
Explicit recovery handles abandoned containers/records after a hard crash.

Records live in ignored `.local/executions/`, with no database or public network service.
See [the record contract](execution-record.md),
[schema](execution-record.schema.json) and [implemented security limits](../SECURITY.md).
The web API is intentionally disconnected from this local CLI.

## Implemented bounded generation workflow

`generation/provider.py` implements the controller-side Vultr HTTPS adapter and an
explicit offline fake provider. No other live provider is available. A trusted controller
transport process makes one request under a total deadline and byte cap, without retries
or redirects. Configuration, usage and worst-case reservations are persisted separately
from sandbox evidence. Credentials remain in that controller boundary. The approval
ledger survives reloads; failures retain reserved capacity.

`generation/workflow.py` builds a prompt from the extraction contract and one synthetic
development input, then requests source. Each script runs through the existing Docker
controller against up to three fixed documents, including one held-out input. Expected
answers are loaded only for local deterministic validation. One eligible failure can
request a corrected script, evaluated again from the first case. Feedback contains the
prior script and a generic failure code; no additional document or expected answer is
sent. Any second failure, unsafe artifact, containment/infrastructure failure or cleanup
failure terminates the workflow. Limits and validators are controller code, not model
parameters. No provider-returned Python executes on the host.

Workflow records and per-attempt generation receipts live under `.local/workflows/`.
Execution record v2 links each task to its workflow/attempt and labels deterministic
fixtures, offline provider fixtures and live Vultr-generated code distinctly. Recovery
marks unfinished workflows/requests abandoned without repeating requests or refunding
budgets. [Inference configuration and authorization](inference.md) documents the exact
plan needed before live requests. Current observed results use only offline responses;
there is no evidence of live inference quality or Vultr deployment yet.

## Product

A technical seller enters an offer and a small list of company websites. Research yields
dated facts, an explicitly labelled fit hypothesis and unresolved questions. A supported
use case can lead to a bounded document-extraction demonstration using permitted public
or synthetic input. The final package includes sources, executed code, outputs, check
results, limitations and an editable unsent introduction.

The workspace will show prospects, research/demo/outreach tabs, an evidence viewer and
actual job progress. Failure to retrieve a source is not evidence of poor prospect fit.
No fabricated qualification scores, contact details, benchmarks or savings.

## Control and execution

The API authenticates users and owns access to saved jobs. A worker controller owns
policy, permitted tools, spend limits, state transitions and retries. Model calls use
Vultr Serverless Inference. Models cannot authorize new tools or budget increases.

The controller sends constrained work to a dedicated execution service. Sandboxes run
browser or generated-code tasks and return bounded artifacts. Credentials stay outside
those environments. Screenshot review uses a compatible Vultr model; deterministic checks
validate schemas and required output behavior independently of the model's self-report.

Start with serial execution. Persist state before dispatch, make retries idempotent and
recover abandoned jobs without silently repeating external actions. Store evidence and
artifacts with their source, capture time, input versions and code revision.

## Intended deployment

Separate Vultr control and runner VMs. PostgreSQL and artifact storage stay in the Vultr
architecture; choose local volumes versus managed services after measuring requirements.
Model API credentials belong only to the controller. The public demo permits bounded
sample jobs and requires quotas/access checks before expensive work.

## Initial scope boundary

One demonstration family, a small prospect set, saved evidence and exportable drafts.
Prospect discovery at scale, CRM integrations, mailbox connections and automatic sending
are later decisions. Publishing the repository does not authorize those operations.
