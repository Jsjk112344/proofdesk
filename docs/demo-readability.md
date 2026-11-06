# Compact demo UI: verification receipt

**Deployed and verified:** https://salesdesk.149.28.51.139.sslip.io

Runtime source commit: `ecf3714`. All 67 installed files matched the release manifest.
Archive SHA-256: `27c29612c0933663f7176836ec0d69b24e259c645ae5603881819f1981e72c4c`.
A rollback snapshot was taken; stores, caches, ledgers and service configuration retained.

The screenshots use a fresh Chromium context at **1440×900**, directly against the public
VM without local asset overrides or mocked API responses. All API calls use normal session
cookies, workers, cached responses and approval endpoints. Backend code, validators,
contracts, stored-data formats, sandbox policy, approval binding and replay are unchanged.

## Default document heights

Heights are CSS pixels, with disclosures closed. A 900 px viewport gives document height
a 900 px minimum even when the content fits comfortably above it.

| Screen | Before | After, deployed |
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

The canonical `salesdesk-*.png` screenshots were also refreshed from this deployed run.

## Observed checks

- TypeScript/Vite build and disposable mocked-API browser suite passed.
- Direct public browser passed: one filled primary action above fold, no default timestamps
  or hashes, compact activity, collapsed full analysis/edit/Advanced/sources, preparation
  and authenticated download, reload, proposal-edit invalidation, exact-version draft
  review and invalidation, and Research/Demonstration/Verification access.
- Desktop/mobile had no page errors or horizontal overflow.
- Real HTTP journey passed on the deployed release: Docker execution, reproducibility,
  stale approval refusal, scheduled packet completion and cross-session isolation.
- Backend diff was empty for the presentation change. Campaign approval and draft-review
  request handlers were compared with the preceding implementation and are unchanged.

## Earlier SSH blocker

The first deployment attempt timed out on SSH port 22 while HTTPS remained healthy.
Integration previews were captured with local frontend assets and explicitly labelled as
previews. On retry, SSH worked; the release was installed and all public checks above were
rerun without overrides. The screenshots and measurements on this page now represent the
deployed application. Historical blocker evidence remains in STATUS.md.
