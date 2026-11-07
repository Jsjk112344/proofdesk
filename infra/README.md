# SalesDesk deployment on Vultr

Public URL: https://salesdesk.149.28.51.139.sslip.io

Existing VM: `149.28.51.139`, SSH root with `~/.ssh/id_ecdsa`, hostname proofdesk-web,
Ubuntu 24.04, EWR (New Jersey), two logical CPUs and about four GiB RAM observed.
Application: `/opt/proofdesk`, systemd `proofdesk`, non-root controller user with Docker
access. FastAPI binds to loopback; Caddy handles public HTTPS. No new VM was provisioned.

## Dealer runtime

The default UI is the dealer group dashboard. The separate dealer SQLite store is
`.local/dealer/experiments.sqlite`; it reuses the existing Store and scheduler/lease APIs.
`SALESDESK_DEALER_CONCURRENCY=6` controls rooftop fan-out, bounded to 1–12. The service's
1.5-GiB cgroup cap accommodates controller and worker processes. Individual Docker caps
remain 128 MiB and half CPU; no sandbox policy was relaxed.

`/etc/systemd/system/proofdesk.service.d/dealer.conf` supplies the plan directory
`/opt/proofdesk/.local/dealer-plans` and concurrency. The existing root-only inference
configuration supplies the key. Accepted replay files remain in `.local/replays/`, and
`.local/dealer-sample-review.json` holds the accepted sample baseline. Fresh public
sessions can read it immediately; Run now always executes actual sandbox jobs.

Operator-only sample/replay/plan/ledger installation is separate from the source release.
Hash-check allowlisted files. Never replace a live ledger with an older or disconnected
copy; preserve existing exhausted ledgers. Local live acceptance was stopped before VM
spend authority was handed over. No credentials enter an archive or a Docker sandbox.

A full direct public run succeeded with six concurrent children and an observed controller/
worker peak of 641.59 MiB. See STATUS.md for release-specific elapsed time and memory.
Use `scripts.check_dealer_browser --screen journey` for direct acceptance; the legacy
experiment journey remains an additional retained-route check.

## Public configuration

`infra/Caddyfile.public` and `infra/proofdesk-public.conf` are installed with
`demo.example.invalid` replaced by `salesdesk.149.28.51.139.sslip.io`. Both the upstream
Vultr firewall and UFW allow TCP 80/443. Caddy obtained a trusted Let's Encrypt certificate.
The API remains on 127.0.0.1:8000; only Caddy is public.

A root-only systemd inference drop-in configures public live mode, the inference key and
separate analysis/prospect budget plans in ignored `.local/`. Accepted replay responses
are stored in `.local/replays/`. Credentials, plans, ledgers and the raw dataset are never
bundled or served. No resource credentials are passed to disposable Docker sandboxes.

Keep one API worker. Seeding uses the normal durable scheduler and prospect workers and
counts against session/global quotas. See [public-demo.md](../docs/public-demo.md).

## Update the private release (with rollback)

From the repository root:

```bash
npm --prefix frontend run build
uv run python -m scripts.build_release
tar -tzf .local/deployment/release.tar.gz | head
cat .local/deployment/release.sha256
```

The bundle is an explicit allowlist: runtime Python (including `backend/app/sales` and
`backend/app/experiments`), synthetic fixtures (including `fixtures/prospects`), compiled
frontend, locked dependencies, security/license docs, service unit and installer, plus the
sanitized `.local/inference-checkpoint.json`. `.env`, SSH keys, approvals, ledgers, workflow
records, prospect records, the raw dataset, the experiment store and screenshots are excluded.

On the VM, keep a rollback snapshot, extract, resync and restart:

```bash
ssh -i ~/.ssh/id_ecdsa root@149.28.51.139
set -e
stamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p /opt/proofdesk-rollback
tar -C /opt --exclude='proofdesk/.local' --exclude='proofdesk/.venv' --exclude='proofdesk/.tools' \
  -czf /opt/proofdesk-rollback/proofdesk-$stamp.tar.gz proofdesk
systemctl stop proofdesk
# copy the new bundle to /root/release.tar.gz first, verify its SHA-256, then:
tar -C /opt/proofdesk -xzf /root/release.tar.gz
cd /opt/proofdesk && .tools/bin/uv sync --locked --no-dev --python /usr/bin/python3
install -d -m 0700 -o proofdesk -g proofdesk .local/experiments .local/data-research/hillstrom
# first time only: copy the pinned CSV to /root/hillstrom.csv, verify its SHA-256, then
install -m 0600 -o proofdesk -g proofdesk /root/hillstrom.csv .local/data-research/hillstrom/hillstrom.csv
runuser -u proofdesk -- .venv/bin/python -m backend.app.experiments import
install -m 0644 infra/proofdesk.service /etc/systemd/system/proofdesk.service
systemctl daemon-reload && systemctl start proofdesk
curl --fail http://127.0.0.1:8000/api/health
```

The importer verifies the exact byte count and SHA-256 before parsing and refuses a changed
file; re-running it on the same file is idempotent.

To roll back, stop the service, extract the snapshot over `/opt/proofdesk` (it excludes
`.local`, so records survive), resync and start again. `release.json` in the install
directory records each deployed file hash, baseline commit and dirty-tree state.

A fresh install on an inspected host uses `bash /opt/proofdesk/infra/install-private.sh`
as root (installs distribution Docker, Python venv tooling, pinned uv, locked runtime
dependencies, the pinned task image, the `proofdesk` user and the service). It never
copies `.env`, enables model spending or installs public ingress.

## Verification

```bash
curl --fail https://salesdesk.149.28.51.139.sslip.io/api/health
uv run python -m scripts.check_experiment_journey \
  --base-url https://salesdesk.149.28.51.139.sslip.io \
  --output .local/deployment/public-journey.json
```

A successful health check is not a complete journey. Verify fresh-session initialization,
real job completion, packet download, cross-session refusals and the browser interface.
STATUS.md records the actual observations and any failed attempts.

## Recovery

Preserve `.local` and root-owned service configuration. Keep a runtime rollback archive
before replacing the allowlisted release. Never delete or reset budget ledgers. Use
`systemctl restart proofdesk` and verify health before requesting a journey; startup can
briefly return 502 through Caddy. Caddy certificate failures need both firewall layers
checked and the issuer's retry window respected.

The owner manages credit balance, compute billing and eventual teardown. No account
billing API credential is configured here; token-cost estimates are not billing receipts.
Stopping the application or Caddy does not stop VM charges.
