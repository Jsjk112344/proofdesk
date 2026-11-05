# Architecture and the prospect journey

SalesDesk is a sales agent for technical sellers. The implemented product journey is:
offering + prospect website → bounded public-page research → evidence brief → demonstration
decision → optional sandboxed demonstration → editable, unsent outreach draft → human
review bound to the exact draft version. It is privately deployed on the owner's Vultr VM.

Two live Vultr model requests (earlier code-generation checks) failed validation and no
successful live inference has been observed yet. The journey therefore runs today in
**rule-based mode**, which is labelled everywhere; live model mode is implemented behind the
same validated contracts and awaits an authorized live run.

## Components

**React workspace** (`frontend/`): a landing form for the offering and prospect website
with a labelled synthetic sample, then a prospect workspace with Research, Demonstration
and Outreach views and a secondary Technical details view (saved events, model request
diagnostics, sandbox evidence, extractor source, historical live inference checks). The
generation mode of every brief and draft is shown as a badge.

**API** (`backend/app/main.py`): anonymous HttpOnly/SameSite session capabilities,
same-origin JSON checks, bounded bodies, idempotent prospect creation, draft edits and
reviews, cross-session 404s, and the retained extraction-run endpoints. One Uvicorn worker.

**Prospect store** (`backend/app/sales/prospects.py`): atomic `.local/prospects/<id>/`
records holding offering, target (public URL or labelled sample), ownership hash, saved
events, sources, brief, demonstration decision/result, draft versions, review state and
sanitized model diagnostics. Quotas: one active job, five per session, twenty total.

**Sales worker** (`backend/app/sales_worker.py` → `sales/agent.py`): a trusted
subprocess per prospect that fetches pages, builds the brief, applies the demonstration
rule, runs the sandbox through the existing execution controller, drafts, and saves
progress after every stage. A restarted API marks abandoned jobs failed without rerunning.

**Retrieval** (`sales/retrieval.py`): hostname-only URLs over http/https on default ports;
all resolved addresses must be globally routable (private, loopback, link-local,
multicast, reserved, unspecified, IPv4-mapped and 6to4/Teredo forms are refused, and one
bad answer blocks the host); the TCP connection is pinned to the validated address with
TLS verification against the hostname; at most three redirects, each re-validated; 512 KiB
per page, HTML/text only, no compressed bodies, per-page and total deadlines; at most four
same-site pages chosen by informational path hints. Pages are untrusted data.

**Evidence** (`sales/evidence.py`): sources numbered in fetch order; claims are verbatim
sentences ranked by document-handling and manual-work terms; company summary from the
description or first descriptive sentence; fixed unknowns list; the demonstration decision
is a controller rule over cited claims (`run`, `skip_irrelevant`,
`skip_insufficient_evidence`). A retrieval failure yields the insufficient-evidence path.

**Contracts** (`sales/contracts.py`): separate validators for executable Python source,
the research brief JSON and the outreach JSON. The research contract requires every
source id to be a fetched source and every excerpt to be verbatim text from it, accepts a
claim's restatement only when it is built from its own quotation's words and numbers
(`text_kind: grounded_restatement`, or `verbatim`), keeps the company summary as a
labelled `model_summary` interpretation, and refuses quantities in the summary,
hypothesis, unknowns or relevance reason that no quotation supports. The outreach
contract allows only known claim ids; a quantity in a paragraph must appear, counting the
same thing, in an excerpt that paragraph cites, the offering or a verified demonstration
summary; savings language, named greetings and demonstration mentions without a verified
result are refused. Records carry `verification: verbatim_quotation` on quotations and
`text_kind` on interpretations so the UI never presents a restatement as a verified fact.
Rejections carry a bounded diagnostic (stage, field path, expected/observed types, head
classification, quantity kind and attribution) and never the rejected text. These checks
are lexical and attributional; they do not establish truth.

**Provider** (`generation/provider.py`): one shared bounded transport, usage accounting
and pessimistic reservations for all contracts; `complete()` dispatches one request and
hands the assistant content to exactly one contract. The documented response `model`
echo is recorded rather than rejected; `finish_reason`, reasoning presence and
`completion_tokens_details.reasoning_tokens` are recorded. A replay provider serves
previously accepted live responses for byte-identical requests without a charge.

**Drafting** (`sales/drafting.py`): controller-owned greeting, sign-off placeholders and
footnotes; a template draft in rule-based mode; prompts and rendering for live mode. A
failed demonstration is described as left out; a skipped one is not mentioned.

**Execution** (`execution/`): unchanged disposable Docker sandbox, limits, strict-JSON
artifact validation against the expected answer as canonical JSON values, and cleanup
verification, now also used for the demonstration step.

## Trust boundaries

- The controller (API, worker, CLI) owns policy, quotas, budgets, credentials and records.
  Models propose; deterministic code decides. Page text and model output never authorize
  tools, spending or sends; there are no sends.
- The sales worker receives the inference credential only when the operator configures
  live mode; the Docker task environment never does (`env -i` allowlist).
- Only the fixture extractor and labelled synthetic documents enter the demonstration
  sandbox. Prospect pages never do.
- Review binds to the draft hash; an edit creates a new version and clears the review.

## Deployment

A single Ubuntu VM on Vultr runs the API, controller, retrieval and Docker daemon under a
non-root controller user, bound to loopback; access is through an SSH tunnel. No public
ingress, HTTPS, domain or inference credential is deployed. See [infra/README.md](../infra/README.md).

## Out of scope

No CRM, Slack, mailbox connection, bulk lead discovery, autonomous sending, browser
automation, paid search, new cloud services or generic agent framework. Only one
demonstration family exists; other offerings get research and a draft only.
