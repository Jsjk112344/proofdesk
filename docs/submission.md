# LabLab submission fields

Prepared copy for Challenge 2, Powering the Future of Work. This is not a submission receipt.
Verify the final logged-in form's field names and limits before pasting.

**Title:** SalesDesk — Sell more: Your AI sales analyst

**Short description:** SalesDesk measures campaign results, proposes your next move and prepares an approved packet while you are away. Two entry doors, one analyst loop, powered by Vultr compute and Serverless Inference.

**Long description:**

SalesDesk helps sales managers turn campaign evidence into a next move and a prepared
handoff. The home screen has two entry doors: See what worked for teams with campaign
history, and Starting from zero for teams researching their first customers.

The campaign workspace analyses a genuine public, randomized e-mail campaign covering
64,000 customers. A saved plan runs through a durable worker on a Vultr VM and a disposable
Docker sandbox. SalesDesk presents conversion, visits, spend and uncertainty, then uses
Vultr Serverless Inference to propose a reading and an editable next move. A person approves
an exact version and schedules packet preparation. They can close the tab and return to a
ready-for-review Markdown packet. Analyst activity shows the recorded steps and Verification
keeps detailed evidence available without crowding the main workflow.

The prospect workspace researches an example company, prepares a sourced brief, makes a
demonstration decision and creates an unsent outreach draft. Public prospect examples are
explicitly synthetic; the demonstration really executes in Docker. No outreach is sent.

Vultr hosts FastAPI, SQLite, the scheduler, workers and Docker execution in EWR, New Jersey.
Caddy handles HTTPS. Qwen 3.8 Flash Next runs through Vultr Serverless Inference; analysis,
research and outreach contracts have passed live. Identical requests can use accepted,
revalidated cached responses, with that provenance in Verification. Human approvals remain version-bound.

**Challenge/category:** Powering the Future of Work / Sales Operations

**Technology tags:** Vultr Cloud Compute, Vultr Serverless Inference, Qwen, Python,
FastAPI, React, TypeScript, Docker, SQLite, Caddy, AI Agents, Workflow Automation

**Demo URL:** https://salesdesk.149.28.51.139.sslip.io

**Repository:** https://github.com/Jsjk112344/salesdesk

**License:** MIT for original code; dataset and dependency notices in THIRD_PARTY.md.

**Video:** Upload the recording made from [demo-script.md](demo-script.md).

**Slides:** Upload the PDF exported from [slides.md](slides.md).

**Cover:** [Verified public home screenshot](assets/salesdesk-home.png).

**Submission status:** Prepared, not submitted. Video recording and PDF export remain open.
Target supplied by owner: November 8, 2026 at 16:00 ET; deadline 18:00 ET.
