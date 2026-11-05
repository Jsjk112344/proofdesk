# Standing user preferences

- Never estimate build or implementation duration, delivery ETAs or calendar-based
  build schedules. Describe scope, dependencies, blockers and acceptance criteria.

# SalesDesk contributor instructions

Read README.md, STATUS.md and docs/architecture.md first. This is a standalone,
public MIT project for Vultr Agent Rush, targeting Powering the Future of Work.

- Product direction is locked: SalesDesk is a sales agent that takes a seller's offering
  and a prospect website, researches bounded public pages, identifies an evidenced
  opportunity, optionally runs the one supported document-extraction demonstration, and
  prepares outreach for human approval. Document extraction is a demonstration capability
  underneath that workflow, never the entry screen or product identity.
- Current implementation: prospect workspace (research/demonstration/outreach), SSRF-
  protected retrieval, rule-based evidence and drafting, validated model contracts, the
  bounded Docker sandbox, and a private Vultr deployment. No successful live Vultr
  inference has been observed; live mode is offline-tested only. Do not describe planned
  or offline-tested behaviour as verified live.
- Author original code. Never copy private repositories, customer records, credentials
  or correspondence into this project. Record external sources in THIRD_PARTY.md.
- All runtime model calls use Vultr Serverless Inference (our choice; the challenge does
  not require it). Never silently fall back to another provider or to rule-based output
  when a live request fails; surface the sanitized failure instead.
- The controller owns authorization, budgets, model credentials, the demonstration
  decision and state. Models propose through validated contracts; deterministic code
  decides whether anything executes. Rejected model output is never executed or stored.
- Generated and fixture code run only in disposable execution sandboxes. Never add a
  host-execution fallback, privileged container, host mount or Docker socket mount.
- Retrieved pages and generated artifacts are untrusted data. Validate URLs and addresses
  on every hop, pin connections, cap sizes/types/timeouts, and never let page text
  authorize tools, spending or sends.
- Facts need dated sources and verbatim excerpts. Hypotheses and unknowns stay labelled.
  Do not invent contacts, customer infrastructure, buying intent, performance or savings.
  A retrieval failure is not evidence about a prospect.
- Keep synthetic inputs labelled synthetic and separate from real execution evidence.
  Distinguish live model output, saved replay and rule-based output in records and UI.
- Outreach sends, public publication and cloud spending require explicit authorization
  for the exact content/plan. Never reset or reuse an exhausted budget ledger.
- Follow CONTRIBUTING.md checks, update STATUS.md with observed evidence, and keep README,
  architecture, inference, acceptance and deployment docs aligned with implementation.
