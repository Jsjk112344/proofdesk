#!/usr/bin/env bash
# Run as root on the existing, inspected Ubuntu host after extracting the reviewed bundle.
set -euo pipefail
cd /opt/proofdesk
test "$(id -u)" = 0
test -f frontend/dist/index.html
test -f uv.lock
test ! -e .env
if ! command -v docker >/dev/null; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io python3-venv
fi
systemctl enable --now docker
if ! id proofdesk >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /var/lib/proofdesk --shell /usr/sbin/nologin proofdesk
fi
usermod -aG docker proofdesk
python3 -m venv .tools
.tools/bin/pip -q install uv==0.12.10
.tools/bin/uv sync --locked --no-dev --python /usr/bin/python3
docker pull "$(cat infra/task-image.txt)"
install -d -m 0700 -o proofdesk -g proofdesk .local .local/executions .local/web-runs
chown -R proofdesk:proofdesk .local
install -m 0644 infra/proofdesk.service /etc/systemd/system/proofdesk.service
systemctl daemon-reload
systemctl enable --now proofdesk
systemctl is-active --quiet proofdesk
echo 'Private service installed at 127.0.0.1:8000; no public ingress configured.'
