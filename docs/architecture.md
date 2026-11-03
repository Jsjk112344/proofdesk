# Architecture and first workflow

This is the intended design. Only the health endpoint and bootstrap screen exist today.

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
