# Security

## Current status

The HTTP application is an experiment workspace plus a supporting prospect workspace. The
experiment workspace serves aggregates of a pinned public dataset (never raw rows), saves
analysis plans, runs a fixed analysis program in the disposable Docker sandbox through
lease-based jobs claimed by the API process's scheduler, validates and reconciles the result,
and lets a person edit, approve and schedule a next-experiment packet. The prospect workspace
fetches a bounded set of public pages, builds an evidence brief, optionally runs the one
supported demonstration in the same sandbox and prepares an unsent draft. Both are publicly available through Caddy HTTPS on the owner's Vultr VM; the API listens
on loopback. Live analysis, research and outreach have passed their contracts. Public sessions
prefer validated exact-input replay; credentials remain controller-only. There are no uploads, arbitrary code, sends, raw-dataset
routes, CRM or mailbox integrations. Anonymous session capabilities scope records;
user-account authentication is not implemented. Observed checks are in [STATUS.md](STATUS.md).
This is not a production deployment or proof against every container escape.

## Experiment boundary

- The raw dataset lives only in ignored local storage (mode 0600 on the VM) and is read by
  the importer alone; the sandbox receives a typed derivative, the API serves aggregates.
- Every plan names original arms only; every result is accepted only through the analysis
  contract and reconciliation (counts and cents against the importer's Decimal aggregates,
  intervals against the controller's implementation, hashes binding data, plan, program and
  input); every displayed number derives from a validated artifact or a labelled assumption.
- A model receives validated metrics and limitations, never rows, credentials or contacts,
  and may cite numbers only through metric placeholders rendered in code; raw numbers, ROI
  wording, unknown ids and actions against the historical records are refused. The model
  cannot change rows, methods, confidence levels, allocation, approvals or job destinations.
- Jobs are claimed atomically under a lease; every worker write is conditional on that lease;
  artifacts are unique per job; a lost or terminated worker is requeued once or failed; a
  restarted API runs the existing sandbox recovery before dispatching again. Approval binds
  to the proposal, artifact and plan hashes and is re-checked by the worker.
- Quotas bound plans, runs, tasks and queued jobs per session and in total; public demo mode
  lowers them and shortens the due horizon. Cross-session reads answer 404.

## Retrieval boundary (SSRF)

- URLs must be `http`/`https` with a hostname (no userinfo, no IP literals, default ports
  only, no `localhost`, `.local`, `.internal`, `.arpa` and similar suffixes, ≤ 2,048 chars).
- Every address returned by DNS must be globally routable. Private, loopback, link-local,
  multicast, reserved, unspecified, IPv4-mapped IPv6, 6to4 and Teredo addresses are refused,
  and a single bad answer blocks the host (no rebinding through mixed answers).
- The TCP connection is opened to the exact validated address; TLS verifies the hostname.
  Each redirect (at most three) is re-validated and re-resolved. Off-site links are never
  followed; discovered pages must be same-site.
- Per page: 512 KiB body cap (declared and read), HTML/text content types only, no
  compressed bodies, 10-second socket timeout; 45 seconds per prospect; at most four pages.
- Page text is stored as evidence and treated as data. It never becomes an instruction,
  tool authorization, budget change or send. A fetch failure or policy refusal is recorded
  on the source and leads to the insufficient-evidence path, never to a verdict.
- No authenticated scraping, browser automation, paid search or caching across users.

## Workspace boundary

- Prospect creation validates URL syntax and host policy in the API; address checks happen
  in the worker. Offering text is bounded (20–1,500 chars); bodies are capped at 16 KiB.
- Random 256-bit session cookies are HttpOnly and SameSite Strict; owners are stored as
  hashes; another session receives 404 for a prospect, draft or review.
- Same-origin JSON/custom-header checks, idempotent creation and edits by request id, one
  active prospect job, five per session and twenty per checkout by default.
- Review binds to the draft's SHA-256; an edit creates a new version, records the previous
  one and clears the review. Stale reviews and edits are refused with
  `draft_version_conflict`. Nothing is sent by SalesDesk.
- The API launches a trusted worker subprocess with an allowlisted environment. The
  inference credential is passed only when the operator configures live mode; the Docker
  task environment never receives it (`env -i` allowlist, unchanged).
- Only the fixture extractor and labelled synthetic documents enter the sandbox. Prospect
  pages never do. Results are shown only when the saved artifact hash matches.
- Prospect worker loss is terminal; restart marks abandoned prospects failed without
  rerunning. Experiment jobs are requeued once by lease recovery. CSP forbids inline scripts
  and foreign resources; task text is escaped by React.

## Model boundary

- Four separate contracts validate model content: executable source, research JSON,
  outreach JSON and the analysis reading JSON (metric placeholders only; see above). Research citations must name fetched sources and quote verbatim text; a
  claim's restatement may use only words and numbers from its own quotation, so an
  unrelated assertion cannot be accepted because its quotation exists; summaries and the
  hypothesis are kept as labelled interpretations and may not introduce quantities absent
  from the quotations. Outreach may cite only known claims, may use a quantity (numeral,
  written number, quantifier, percentage or amount) only when the same number counts the
  same thing in an excerpt the paragraph cites, the offering or a verified demonstration,
  cannot mention a demonstration unless verified, use savings or guarantee language, or
  address a named person. These are lexical and attributional checks against captured
  evidence; they do not establish truth. Fabricated citations stop the job.
- Rejections record only a bounded diagnostic (stage, field path, expected/observed types,
  head classification, counts). Rejected content is never stored, executed or shown.
- The controller decides the demonstration from validated claims; the model's relevance
  opinion is recorded, not obeyed. Prompts wrap offering and page text as data.
- Requests use reasoning disabled and JSON-object output for the sales contracts, under a
  plan-bound deadline, token caps and cost ceiling. No retries, no fallback provider.
- Live spending requires an exact owner-approved plan and a controller credential. Each
  request reserves its worst case in a durable local ledger before dispatch; failures never
  refund; the exhausted earlier ledger is untouched. Replay serves only previously accepted
  responses for byte-identical requests.

## Execution boundary (unchanged)

Fresh named container per task on a digest-pinned image; UID 65532, all capabilities
dropped, `no-new-privileges`, default seccomp, private PID/IPC/cgroup namespaces,
read-only root, `--network=none`, no mounts, devices, Docker socket or credentials;
0.5 CPU, 128 MiB RAM without swap, 32 processes, bounded tmpfs, 16 KiB logs, 64 KiB
archive, five-second deadline with forced removal (thirty seconds and a 1 MiB typed input for
the analysis profile; scripts always ≤ 32 KiB); kernel limits read back before task code; only
`out/result.json` ≤ 16 KiB accepted, parsed as strict JSON and compared with the expected
answer as canonical JSON values (not original bytes) or, for the analysis profile, checked by
the result contract; verified container absence required for success, with bounded repeated
removal when a killed client's `create` lands late; explicit crash recovery at CLI and API start.
See [docs/execution-record.md](docs/execution-record.md).

## Local limitations

The controller, checkout, Docker daemon, pinned image and host kernel are trusted. The
Docker group on the VM has host-level authority and belongs only to the controller user.
Observations come from ordinary Docker on macOS (Colima) and the Vultr VM; they are not a
general escape guarantee and SalesDesk does not claim sandbox escape protection. Retrieval
protects against private-network access from the controller host, not against a public
site serving misleading content; such content is quoted verbatim with its source so a
reviewer can judge it. Contract checks compare model wording with captured evidence; they
cannot detect a grounded restatement whose word order or negation changes the meaning, a
quantity reused for a different subject that shares a head word, or promises phrased
outside the refused word list. Every draft is presented for human review for that reason.
Local records have no aggregate retention quota. Hard crashes require explicit recovery.

## Reporting

Use GitHub private vulnerability reporting for this repository when enabled. Avoid
posting credentials, exploit payloads containing private data, or private records in
public issues.
