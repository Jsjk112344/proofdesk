# ProofDesk contributor instructions

Read README.md, STATUS.md and docs/architecture.md first. This is a standalone,
public MIT project for Vultr Agent Rush, provisionally targeting Blast Radius Zero.

- Current implementation is a local deterministic execution CLI and web bootstrap.
  Do not describe planned agent, security, deployment or submission behavior as verified;
  local Docker observations do not establish Vultr deployment or general escape protection.
- Author original code. Never copy private repositories, customer records, credentials
  or correspondence into this project. Record external sources in THIRD_PARTY.md.
- All runtime agent model calls, including verification and drafting, must use Vultr
  Serverless Inference for this track. Never silently fall back to another provider.
- The controller owns authorization, budgets, model credentials and state. Models
  propose actions; deterministic code decides whether they may execute.
- Generated code and browser actions belong in disposable execution sandboxes.
  Never add a host-execution fallback, privileged container, host directory mount
  or Docker socket mount inside a task sandbox. Read SECURITY.md.
- Treat retrieved content and generated artifacts as untrusted. Validate URLs on
  every redirect, restrict egress and validate artifact paths/types/sizes.
- Facts need dated sources. Hypotheses and unknowns remain labelled. Do not invent
  contacts, customer infrastructure, buying intent, performance or savings.
- Outreach sends and public artifact publication require explicit authorization for
  the exact content. Existing authorization persists; ordinary local work proceeds.
- Cloud spending needs a resource plan and authorized cap. No paid calls in CI.
- Keep local examples synthetic and labelled. Keep evidence of real execution
  separate from fixture/replay output. Stop jobs on limits and preserve failure reasons.
- Follow CONTRIBUTING.md checks, update STATUS.md with observed evidence, and keep
  README setup/architecture aligned with implementation. Never claim submission
  without a receipt or containment from an ordinary web-container build.
