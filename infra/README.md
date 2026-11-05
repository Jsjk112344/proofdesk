# Private Vultr deployment

Selected challenge: **Powering the Future of Work**. The owner supplied an existing
Ubuntu 24.04 x86-64 VM; SalesDesk is installed and verified on it as a private, loopback-only
service. No VM, subscription, GPU or inference resource was provisioned by this project.
VM billing and eventual teardown remain owner-managed. No inference credential, approval or
budget ledger is deployed; the service runs in rule-based (no model) mode.

## Verified facts

- Host: `149.28.51.139`, SSH user `root`, identity `~/.ssh/id_ecdsa`, hostname `proofdesk-web`.
- Install path `/opt/proofdesk`; systemd service `proofdesk` running as the non-root
  `proofdesk` user (Docker group); API bound to `127.0.0.1:8000` only.
- Docker 29.1.3, x86-64, cgroup v2, default seccomp/AppArmor; pinned task image present.
- Records on the VM: `.local/web-runs/`, `.local/executions/` and, after this update,
  `.local/prospects/`. They are preserved across updates.

## Inspect through SSH

```bash
ssh -i ~/.ssh/id_ecdsa -N -L 18000:127.0.0.1:8000 root@149.28.51.139
```

Open http://127.0.0.1:18000. The page and API run entirely on the VM; port 18000 is only a
local tunnel endpoint. The app is not exposed to the public Internet. Real-URL research runs
from the VM's network with the SSRF policy; the sample scenarios read synthetic pages from
disk and never make a request.

## Update the private release (with rollback)

From the repository root:

```bash
npm --prefix frontend run build
uv run python -m scripts.build_release
tar -tzf .local/deployment/release.tar.gz | head
cat .local/deployment/release.sha256
```

The bundle is an explicit allowlist: runtime Python (including `backend/app/sales`),
synthetic fixtures (including `fixtures/prospects`), compiled frontend, locked
dependencies, security/license docs, service unit and installer, plus the sanitized
`.local/inference-checkpoint.json`. `.env`, SSH keys, approvals, ledgers, workflow
records, prospect records and screenshots are excluded.

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
install -m 0644 infra/proofdesk.service /etc/systemd/system/proofdesk.service
systemctl daemon-reload && systemctl start proofdesk
curl --fail http://127.0.0.1:8000/api/health
```

To roll back, stop the service, extract the snapshot over `/opt/proofdesk` (it excludes
`.local`, so records survive), resync and start again. `release.json` in the install
directory records each deployed file hash, baseline commit and dirty-tree state.

A fresh install on an inspected host uses `bash /opt/proofdesk/infra/install-private.sh`
as root (installs distribution Docker, Python venv tooling, pinned uv, locked runtime
dependencies, the pinned task image, the `proofdesk` user and the service). It never
copies `.env`, enables model spending or installs public ingress.

## Public demo mode (prepared, not activated)

The application can run as a public demo: `PROOFDESK_PUBLIC_DEMO=1` limits research to the
labelled synthetic scenarios (unless `PROOFDESK_PUBLIC_URL_ALLOWLIST` names a host), lowers
the per-session allowance to three prospects, raises the bounded total to 100 by default,
labels the mode in the API and UI, and keeps live model mode off unless
`PROOFDESK_PUBLIC_LIVE=1` is set together with an approved plan and credential. The
prepared ingress is [Caddyfile.public](Caddyfile.public) (TLS termination on the existing
VM) with the systemd drop-in [proofdesk-public.conf](proofdesk-public.conf). Neither is
installed; [docs/public-demo.md](../docs/public-demo.md) is the activation proposal.

## Live model mode on the VM (not enabled)

Enabling live mode would require an owner-approved plan file on the VM, the credential in
the service environment (`PROOFDESK_SALES_LIVE_PLAN`, `VULTR_INFERENCE_API_KEY` via a
root-only drop-in, never in the bundle) and an authorized budget. None of that is deployed.

## Check the service and runtime

```bash
systemctl status proofdesk --no-pager
curl --fail http://127.0.0.1:8000/api/health
cd /opt/proofdesk
runuser -u proofdesk -- .venv/bin/python -m backend.app.execution probe all
runuser -u proofdesk -- .venv/bin/python -m backend.app.sales run --sample harbor-vale-freight
```

One API worker; anonymous session cookies; five prospects per session and twenty total
persisted by default (`PROOFDESK_WEB_MAX_PROSPECTS`). There is no user-account system,
upload path or paid-model endpoint. Public activation needs exact-content authorization,
reviewed ingress/HTTPS and an access policy; none has been chosen.

## Recovery and stopping

```bash
systemctl stop proofdesk
cd /opt/proofdesk
runuser -u proofdesk -- .venv/bin/python -m backend.app.execution cleanup
runuser -u proofdesk -- .venv/bin/python -m backend.app.sales cleanup
systemctl start proofdesk
# To leave the app stopped across reboots instead:
systemctl disable --now proofdesk
```

Never delete the inference ledger to retry generation; never use a global Docker prune.
These commands do not delete the VM or stop its billing.

## Browser verification

[Browser test image](browser-test.Dockerfile) is for trusted UI checks against a mocked
API, not for browsing untrusted sites:

```bash
docker build -t proofdesk-ui-check - < infra/browser-test.Dockerfile
uv run python -m scripts.check_browser
```

The runner streams compiled assets and recording-runner journey records into a disposable
container with no network, credentials, host mounts or extra capabilities, checks desktop
and mobile interaction, and collects bounded PNG/JSON outputs without extracting archive
paths onto the host. Screenshots stay ignored under `.local/browser/`.
