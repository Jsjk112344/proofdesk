# LabLab submission fields

Prepared for Challenge 2, Powering the Future of Work. Check the logged-in form’s current
field names and limits. This file is not a submission receipt.

**Title:** SalesDesk — Sell more: Your AI sales analyst

**Short description:** Every night, SalesDesk works every lead across every rooftop:
finds cold leads, matches available cars, prioritises aged inventory and drafts follow-ups.
Dealer-group leaders see the roll-up; store managers approve. Powered by Vultr.

**Long description:**

SalesDesk turns a dealer group’s scattered lead and inventory exports into a morning queue
that store managers can approve. The sample is the fictional Summit Auto Group: 24 rooftops
across the Mountain West, 3,000 cars, 9,000 open leads and 2,400 historical leads. Automotive
is the first vertical for a reusable job, contract and approval engine.

A nightly review fans out one durable child job per rooftop on Vultr. Six workers run
concurrently, each using its own disposable Docker sandbox with unchanged resource and
isolation limits. A fixed analysis program flags cold leads, stale appointments, sold
vehicle interests and slow response. It scores current and in-transit stock at the same
store and nearby sister stores, boosts aged units, and returns three matches per at-risk
lead. Independent controller reconciliation verifies metrics and score components before
anything reaches the interface or model.

Vultr Serverless Inference runs Qwen 3.8 Flash Next through validated rooftop and group
brief contracts. It receives curated metrics and facts, never raw uploaded rows or contact
details. Quantities and vehicle facts use references rendered in code. Unsupported references,
quantities, promises, features and sends are rejected. Accepted identical-input replay is
revalidated and labelled; a real public run still executes the sandbox analysis.

In Sandy, Maria G. asked about a blue RAV4 Hybrid that sold. SalesDesk finds a silver
2024 RAV4 Hybrid XLE with 74 days on lot and drafts a follow-up about her CR-V trade.
The manager can edit, skip or approve a ranked queue. Approval binds an exact version;
Vultr workers then prepare follow-ups.md, crm-tasks.csv and transfer-requests.csv.
Nothing is sent to customers and no transfer is executed.

Group leadership sees the regional map, store ranking, source performance, carrying-cost
assumptions and estimated recoverable gross. Job progress reflects saved worker events,
not a timer. Server-owned 2 AM Mountain Time schedules continue after the browser closes.
Data enters through bounded, session-scoped CSV uploads. Live CRM/DMS connections are next.
The existing Vultr EWR VM hosts FastAPI, SQLite, workers, Docker and Caddy HTTPS.

**Category:** Powering the Future of Work / Sales Operations

**Technology:** Vultr Cloud Compute, Vultr Serverless Inference, Qwen, Python, FastAPI,
React, TypeScript, Docker, SQLite, Caddy, Workflow Automation

**Demo URL:** https://salesdesk.149.28.51.139.sslip.io

**Repository:** https://github.com/Jsjk112344/salesdesk

**License:** MIT original code and synthetic dealer fixtures; external sources/dependencies
are attributed in THIRD_PARTY.md. No private customer data is included.

**Video:** Record/export using [demo-script.md](demo-script.md), then upload.

**Slides:** Export [slides.md](slides.md) as PDF, then upload.

**Cover:** [Group view screenshot](assets/salesdesk-group.png).

**Evidence:** [STATUS.md](../STATUS.md) contains observed full-run wall-clock, memory,
inference requests/spend and public checks. Sample values are synthetic, floorplan is an
entered assumption, and recoverable gross is an estimate from listed figures with possible
repeated units. No measured sales uplift or human time saving is claimed.

**Submission state:** Prepared; not submitted. No receipt exists. Owner-supplied target:
November 8, 2026, 16:00 ET; deadline 18:00 ET. The owner must record the video, export the
slide PDF, check the final form and submit.
