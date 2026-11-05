# Public demo: prepared configuration and activation proposal

Status: **implemented and tested offline; not activated.** Public activation needs the
owner's explicit approval of the hostname, HTTPS configuration, access policy and the
reviewed public content below. Nothing in this document authorizes ingress, DNS changes,
package installation on the VM or public inference spending.

## What a signed-out visitor would get

The same prospect workspace as the private deployment, in **public demo mode**:

- Only the three labelled synthetic scenarios can be researched. The real-website field is
  disabled in the UI and the API refuses real URLs with `public_demo_samples_only` unless a
  host is named in `PROOFDESK_PUBLIC_URL_ALLOWLIST` (empty by default). The SSRF policy is
  unchanged for any allowlisted host.
- Generation mode is **rule-based (no model)** and is labelled as such on every brief and
  draft. A credential present on the VM cannot turn the public app into a paid endpoint:
  live mode additionally requires `PROOFDESK_PUBLIC_LIVE=1`, an approved plan and its
  envelope. No public live inference is proposed here.
- The demonstration runs in the same disposable Docker sandbox on labelled synthetic
  documents; execution evidence, extractor source and cleanup verification are shown.
- Anonymous session cookies scope records: three prospects per session, 100 in total by
  default (`PROOFDESK_WEB_MAX_PROSPECTS`, hard cap 200), one job at a time. Another
  session receives 404 for someone else's prospect. Nothing is sent anywhere.
- The header reads "Public demo · synthetic scenarios · nothing is sent"; the landing page
  carries a labelled note; `/api/health` and `/api/workspace` report `public_demo: true`.

## Proposed URL and ingress

Two options for the hostname; both work with the prepared files unchanged apart from
substituting the name:

1. **Owner-supplied subdomain** (preferred if a domain exists), for example
   `salesdesk.<owner-domain>` with an A record to `149.28.51.139`.
2. **No-DNS fallback**: a wildcard-DNS name such as `149-28-51-139.sslip.io`, which resolves
   to the VM without any DNS setup. It exposes the already-public VM address in the name
   and depends on a third-party resolver; use it only for the judging window.

TLS termination: Caddy from the Ubuntu 24.04 repositories on the existing VM, using
[infra/Caddyfile.public](../infra/Caddyfile.public) (automatic Let's Encrypt certificate,
HTTP→HTTPS redirect, HSTS, 64 KB request bodies, reverse proxy to `127.0.0.1:8000`). The
API keeps binding to loopback. The systemd drop-in
[infra/proofdesk-public.conf](../infra/proofdesk-public.conf) sets public mode, the
allowed host header, the total quota and uvicorn's proxy-header handling so the session
cookie is marked `Secure` behind TLS. Ports 80 and 443 must be opened in the VM firewall
or Vultr firewall group; no other ports change.

## Costs, resources and cleanup

- No new VM, managed service, GPU, database or inference resource. Caddy is a distribution
  package on the existing VM; Let's Encrypt certificates are free.
- Vultr compute billing for the existing VM is unchanged and remains owner-managed. Public
  demo traffic adds Docker demonstration runs bounded by the quotas above.
- Cleanup owner: the executor removes the drop-in and Caddy configuration and closes the
  ports on request; the owner controls DNS and VM teardown. Prospect records created by
  visitors live under `/opt/proofdesk/.local/prospects/` and are demonstration data.

## Checks before activation (done offline) and after (to observe)

Done offline, this checkpoint: API tests for public mode (real URL refused, allowlist honoured,
session quota of three, totals, `public_demo` flags, live mode refused without the public
flag) and the disposable browser check of the public-mode landing page, disabled website
field and sample journey.

To observe after authorized activation, recorded in STATUS.md with the URL:

1. `curl -I https://<host>/` returns 200 with the CSP and HSTS headers; `http://` redirects.
2. A signed-out browser completes the sample journey over HTTPS: brief, demonstration
   decision and verified result, editable draft, review binding, reload.
3. A second browser profile cannot read the first profile's prospect (404) and the
   session quota stops the fourth prospect with a readable message.
4. `/api/health` reports `public_demo: true` and `generation_mode: deterministic`.
5. The private SSH-tunnel path still works; existing records are intact.

## Rollback

```bash
systemctl stop caddy && systemctl disable caddy
rm -f /etc/systemd/system/proofdesk.service.d/public.conf
systemctl daemon-reload && systemctl restart proofdesk
```

Records are untouched by rollback; the service returns to private loopback mode. Closing
ports 80/443 again is part of the same step.

## Authorization requested (not granted by this document)

- The hostname to use (option 1 or 2) and permission to install Caddy and open 80/443.
- Approval of the public content: the current README, fixtures and UI copy as reviewed.
- Confirmation that public live inference is **not** enabled (default) or, separately, an
  approved public plan and envelope if it ever is.
