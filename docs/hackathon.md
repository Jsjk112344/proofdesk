# Agent Rush submission checklist

Selected challenge: **Powering the Future of Work**, confirmed by the owner 2026-11-05.
Rules refreshed 2026-11-05 from the [event page](https://lablab.ai/ai-hackathons/vultr-hackathon)
(now served from lablab.build): a Vultr VM backend deployment, GitHub repository with setup
and documentation, public demo URL, recorded demo video and a clear architecture/use-case
explanation are required. **Vultr Serverless Inference and sandboxing are optional** for
this challenge; SalesDesk keeps both as engineering choices. Judging: application of
technology, presentation, business value, originality. Online build November 3–8, 2026;
no explicit submission hour/timezone was stated on the page. Recheck the actual form.

Sources: [event](https://lablab.ai/ai-hackathons/vultr-hackathon),
[LabLab terms, section 16](https://lablab.ai/terms-of-use), [rule book](https://lablab.ai/hackathon-rules).

## Repository and rights

- [x] Public repository and anonymous access verified in the initial checkpoint.
- [x] MIT license for newly authored project work.
- [x] Existing work and third-party provenance documented.
- [x] README describes setup, current architecture and Vultr use.

Current continuation changes are local and uncommitted; no push or publication is claimed.

## Future of Work build and presentation

- [x] Sales-agent journey implemented: offering + prospect → sourced brief → justified
      demonstration decision → sandboxed demonstration → editable unsent draft → review.
- [x] Private backend/web deployment on the owner's existing Vultr VM, updated and verified.
- [x] Contract corrections for the two reproduced false-claim defects (grounded
      restatements, attributed quantities) with regression tests; documentation describes
      the checks as lexical/attributional, not as factual verification.
- [ ] Successful live Vultr inference for the research/outreach contracts (consolidated
      envelope proposal prepared in docs/inference.md, authorization pending). Rule-based
      mode is the deployed default.
- [ ] Public, reviewed web demo with HTTPS and access controls (public-demo mode, Caddy
      and systemd templates implemented and tested offline; activation proposal in
      docs/public-demo.md awaits the hostname and approval).
- [ ] Recorded demo video, slides and cover.
- [ ] Project description and technology/category tags.
- [ ] Official LabLab submission and receipt.

Phases, dependencies and required authorizations for the unchecked items are in
[docs/plan.md](plan.md). A private loopback deployment does not satisfy the public demo requirement. No prospect
discovery, CRM, Slack or sending exists and none is planned for this entry.

## Items to confirm

Exact deadline/timezone, remote prize eligibility, credit redemption and inference
coverage. No signed-in submission form was inspected; no organizer contact, terms
acceptance, credit redemption or submission was performed.
