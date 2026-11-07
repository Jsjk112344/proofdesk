# Current dealer-group public surface

Public URL: https://salesdesk.149.28.51.139.sslip.io

Fresh sessions load the labelled fictional Summit Auto Group and a saved accepted sample
review. No fake jobs or automatic dealer approvals are seeded. Run now creates 24 actual
rooftop child jobs and a waiting parent; six workers execute on Vultr. Model replay is
accepted exact-input output, revalidated and labelled. Primary UI follows real job events.

The sample has 12–85 at-risk leads per store, including Sandy’s original 40, from
varied source records rather than a queue cap. The stat strip and group brief both
show 1,007 best matches in stock. The sample label stays visible in the scrolling
header and inside the lead drawer. [Recording facts](video/measured-run.json) identify
the accepted sample and its separate live-inference measurement.

CSV uploads are untrusted, session-scoped, 10 MiB/file and 50,000 rows/file, with three-file
validation before replacement. Anonymous workspaces are capped at 200, global jobs at 5,000,
reviews at six per session, and handoff jobs at 72. Per-rooftop analysis also retains the
1 MiB typed-input cap. Concentrated oversized data fails visibly rather than changing limits.
Schedules expire with the anonymous session; run quotas still apply. Owners can pause them.
There is no customer sending or live CRM/DMS connection.

The baseline sample review, accepted model responses, plans, ledgers and credentials are
operator-managed ignored files; they are never included in a public source bundle. The
committed dealer fixture is synthetic input, not proof of live inference or execution.
[STATUS.md](../STATUS.md) records the direct public acceptance and actual accounting.

## Retained legacy public endpoints

The historical sections below describe the unlinked campaign/prospect routes and their
separate quotas. They do not describe the new default dealer dashboard.

# Public SalesDesk demo

URL: https://salesdesk.149.28.51.139.sslip.io

The owner authorized public activation and up to $150 of hackathon credit in AGENTS.md.
The existing Vultr VM hosts Caddy HTTPS, FastAPI, SQLite, the scheduler and Docker workers.
The domain uses sslip.io DNS pointing to the VM. Ports 80 and 443 must be allowed in both
Vultr's attached firewall and the host firewall; the API stays on loopback.

A fresh browser session calls same-origin POST `/api/demo/seed` until its normal workers
have prepared the benchmark packet and unsent prospect draft. The benchmark analysis uses
the genuine dataset. Prospect pages and demonstration inputs are labelled synthetic.
The ready packet's initial approval is explicitly a seeded demo example. Later visitor
changes require their own approval; reload never approves them automatically.

Public limits: three plans, six runs, six tasks, three queued jobs, twelve total jobs per
session, two hundred jobs globally, due times up to one day ahead, three prospects per
session and one hundred prospects globally. Initialization counts against those quotas:
one plan, one run, one task, two jobs and one prospect. No quota is reset on reload.

`PROOFDESK_PUBLIC_DEMO=1` activates these limits and the example initialization.
Public sessions select Live by default. `PROOFDESK_ANALYSIS_LIVE_PLAN`,
`PROOFDESK_SALES_LIVE_PLAN` and `VULTR_INFERENCE_API_KEY` enable the live analyst.
Configuration is outside the release archive in a root-only systemd drop-in. The worker
receives controller credentials; disposable execution sandboxes never receive them.

Identical requests prefer accepted saved responses and revalidate them. Both cached and
new responses show Analyst: Qwen 3.8 on Vultr Inference; cached responses have a cached
response tooltip and retain saved_replay provenance in Verification. New inputs use Vultr
under the existing durable batch/envelope limits.
A genuine failure is visible. No failed step is silently replaced by rule-based text.
Private mode can use explicitly labelled rule-based analysis without a credential.

No outreach sends, uploads, arbitrary code, CRM, Slack or mailbox integration is exposed.
Anonymous HttpOnly sessions scope all plans, jobs, artifacts, packets and prospects.
Source rows, secrets, approval files and ledgers are never served by static routes.

## Verification and recovery

Read STATUS.md for observed external HTTPS, seed, journey and browser checks. The first
ACME attempts failed while upstream ports were closed; after the owner opened the Vultr
firewall and the retry window elapsed, a trusted certificate was issued successfully.

For updates, follow [infra/README.md](../infra/README.md). Keep `.local/`, budget ledgers
and credentials across deployments. Never reset an exhausted ledger to resume calls.
Stop public execution with `systemctl stop proofdesk`; Caddy can remain up for a service
unavailable response. Stop Caddy separately to remove public ingress. The owner manages
VM billing and teardown; stopping the app does not stop VM charges.
