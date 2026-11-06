# Compact demo UI: verification receipt

The frontend is implemented and browser-verified. **Deployment is pending SSH access.**
The public VM still serves the earlier interface. SSH to `149.28.51.139:22` timed out
repeatedly; HTTPS and its existing backend journey remain healthy.

The new screenshots use a fresh Chromium context at **1440×900** with the new compiled
frontend supplied through browser asset overrides. All API calls use the real public
backend, its normal session cookies, workers, cached responses and approval endpoints.
These are integration previews, not proof that the new frontend is deployed. Existing
`schemas`, backend code, validators, contracts, stored record formats and replay are unchanged.
No credentials, redirects, origin headers or API responses were overridden.

## Default document heights

Heights are CSS pixels, with disclosures closed. A 900 px viewport gives document height
a 900 px minimum even when the content fits comfortably above it.

| Screen | Before | After, preview |
| --- | ---: | ---: |
| Home | 900 | 900 |
| Campaign before approval | 4,048 | 1,037 |
| Campaign after approval | 4,366 | 1,078 |
| Prospect | 1,452 | 900 |

The single filled primary action is visible above the fold on all four screens. Campaign
approval/download is around 386–420 px from the top; draft approval is around 234–267 px.
[Exact measurements and screenshot hashes](assets/readability-measurements.json).

## Screenshots

- [Home](assets/readability-home.png)
- [Campaign before approval](assets/readability-campaign-before.png)
- [Campaign after approval](assets/readability-campaign-after.png)
- [Prospect draft](assets/readability-prospect.png)
- [Mobile home](assets/readability-mobile.png)

The prior deployed screenshots retain their original `salesdesk-*.png` names until the
new release can be installed and captured without local asset overrides.

## Observed checks

- TypeScript/Vite build and disposable mocked-API browser suite passed.
- Real-backend browser preview passed: one filled primary action, no default timestamps
  or hashes, compact activity, collapsed full analysis/edit/Advanced/sources, packet
  preparation and authenticated download, reload, proposal-edit invalidation, exact-version
  draft review and invalidation, and Research/Demonstration/Verification access.
- Desktop/mobile had no page errors or horizontal overflow.
- The real HTTP journey passed on the unchanged, existing public backend: Docker execution,
  reproducibility, stale approval refusal, scheduled packets and cross-session isolation.
- Backend diff is empty. Campaign approval and draft-review request handlers were also
  compared with the starting commit and are unchanged.

After SSH is restored: install the prepared allowlisted release, verify its checksum and
manifest, run the fresh browser check without overrides and the HTTP journey, promote the
screenshots and update STATUS. Preserve all `.local` stores, caches and budget ledgers.
