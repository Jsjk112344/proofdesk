# Campaign evaluation: data, method, provenance and limits

SalesDesk's first complete experiment is a **reproduction of a historical randomized e-mail
campaign** from a public benchmark, followed by an approved, scheduled preparation task for a
prospective repeat with a current audience. It is not a new field experiment, it obtains no new
responses and it produces no new sales.

## Source dataset

| Item | Value |
| --- | --- |
| Title | MineThatData E-Mail Analytics and Data Mining Challenge dataset (2008-03-20), Kevin Hillstrom |
| Description | <https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html> |
| Catalog | <https://www.tensorflow.org/datasets/catalog/hillstrom> |
| Original download | `http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv` |
| Independent checksum | <https://raw.githubusercontent.com/tensorflow/datasets/master/tensorflow_datasets/recommendation/hillstrom/checksums.tsv> |
| Bytes / SHA-256 | 3,964,977 / `0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece` |
| Rows / columns | 64,000 / `recency, history_segment, history, mens, womens, zip_code, newbie, channel, segment, visit, conversion, spend` |
| Design | Customers who purchased in the prior twelve months were randomly assigned to a Mens e-mail, a Womens e-mail or no e-mail; visits, purchases and spend were recorded for the two weeks after the campaign (publisher description) |

Arms after import (independently inspected before this feature existed, reproduced by the
importer): Mens E-Mail 21,307 customers / 3,894 visits / 267 purchases / $30,311.69; Womens
E-Mail 21,387 / 3,238 / 189 / $23,038.11; No E-Mail 21,306 / 2,262 / 122 / $13,908.33.

**Rights.** The author publicly invites analysis and sharing of findings. No explicit raw-data
redistribution license was established, so the raw file stays under ignored `.local/`, is never
bundled, served or mirrored, and is not covered by this repository's MIT license. Public artifacts
are attributed aggregate analysis and the reproducible acquisition/importer code. See
[THIRD_PARTY.md](../THIRD_PARTY.md).

**Acquisition.** `uv run python -m backend.app.experiments fetch` downloads the fixed publisher
URL over plain HTTP (the publisher's HTTPS endpoint failed certificate verification during
preparation; TLS verification is never disabled anywhere), caps the body at 4.5 MiB, follows no
redirects, executes nothing and accepts the bytes only if they match the pinned SHA-256. Prefer
the cached file at `.local/data-research/hillstrom/hillstrom.csv`.

## Importer (`backend/app/experiments/ingestion.py`, version `hillstrom-importer-1`)

1. Exact byte count and SHA-256 are verified before parsing.
2. The header must equal the twelve documented columns; every row needs twelve non-empty values.
3. Domains: `recency` 1..12; `history_segment` in the seven published bands; `zip_code` in
   Rural/Surburban/Urban (publisher spelling); `channel` in Phone/Web/Multichannel; `segment`
   in the three arms; `mens`, `womens`, `newbie`, `visit`, `conversion` binary.
4. `history` and `spend` must be finite, non-negative decimals with at most two places; spend is
   converted to integer cents with `Decimal`. Any malformed or missing value stops the import with
   a bounded diagnostic (row, column, observed class). Nothing is repaired, dropped or deduplicated:
   equal-valued rows keep their multiplicity (57,438 distinct lines, maximum multiplicity 31).
5. Output: `manifest.json` (source, hashes, importer version, imported-at, per-arm aggregates,
   validation facts, limitations) and `analysis-input.txt`, a typed derivative with one line per
   assigned customer (`arm, visit, conversion, spend_cents, newbie, channel`, 770,389 bytes,
   SHA-256 recorded). Observation dates remain unknown beyond the documented two-week window;
   the row identifier scheme (dataset hash prefix plus row position) is an import identifier, not
   an identity.

## Analysis plan

A plan fixes: dataset and raw hash; treatment and control among the **original** arms (the third
arm is shown in the source overview and excluded from the comparison); primary outcome purchase
conversion per assigned customer; secondary outcomes visit rate and spend per assigned customer
including zero-spend rows; 95% confidence level; bootstrap seed and resamples (1,000 / 2,000 /
4,000); pre-declared exploratory breakdowns (`newbie`, `channel`). A plan that names a non-original
arm or two identical arms is refused, so historical outcomes can never be attached to an invented
policy. The canonical plan line is hashed (`plan_sha256`) and echoed by the sandbox.

This is a retrospective re-analysis: `retrospective: true`, `preregistered: false`. The plan is
saved for reproducibility, not as preregistration, a blinded test or an untouched holdout.

## Analysis program (`backend/app/experiments/analysis_program.py`, `salesdesk-analysis-1`)

Standard library only, self-contained, executed inside the existing disposable Docker sandbox
(no network, read-only root, 128 MiB, 0.5 CPU, 32 processes, 30 s wall clock for this profile,
1 MiB typed input, 16 KiB result). It:

- reads the header, the plan line and the rows; verifies the arm names, the row count and the
  binary outcomes; hashes its own input;
- computes per-arm counts, visits, purchases, spend (integer cents) and buyers;
- for the planned comparison: Wilson score intervals per arm, the Newcombe hybrid score (method
  10) interval for the difference, relative change only when the control rate is positive;
- for spend: mean per assigned customer and a seeded customer-level percentile bootstrap of the
  difference (resampling *n* customers within each original arm; implemented equivalently as a
  Binomial(*n*, buyers/*n*) count of buyer draws followed by that many draws from the buyers'
  spends, which avoids resampling tens of thousands of zeros). It reports the 2.5/97.5 percentiles
  with linear interpolation, the bootstrap standard error and the SHA-256 of the replicate list;
- writes descriptive exploratory cells (counts and rates, no intervals) for the pre-declared
  breakdowns;
- writes `result.json` with `sort_keys`, so identical input, plan, program and seed produce
  byte-identical output (verified locally and in the real sandbox, including on the pinned file).

Formulas (no code copied): Wilson, E. B. (1927), JASA 22; Newcombe, R. G. (1998), Statistics in
Medicine 17, method 10. Reference values from Newcombe's Table II are regression-tested to four
decimals, and the controller's Wilson bounds are cross-checked by bisection of the score equation.

## Validation and reconciliation (`contracts.validate_result`)

The sandbox artifact is accepted only if: format and program version match; dataset id and raw
hash match the manifest; the echoed input hash equals the hash of the exact task input; the plan
hash equals the saved plan; the row count matches; every arm's counts and spend cents equal the
importer's independent `Decimal` aggregates; the Wilson and Newcombe intervals, rates, means and
relative changes equal the controller's own implementation within 1e-9; the bootstrap carries the
plan's seed and resamples with a finite ordered interval; exploratory totals add up to the arm
sizes. A mismatch fails the run (`reconciliation_mismatch_*`) and leaves no result.

## Metrics and rendering

`contracts.derive_metrics` produces every number a person or model may cite, each with an id,
label, definition, kind, value, interval, interval method, denominator and artifact path (for
example `conversion.difference_pp`, `spend.incremental_per_customer`,
`exploratory.newbie.1.treatment.conversion_rate`). The UI, the packet and the model prompt use
these metrics; `format_metric` renders values with denominators and intervals in code.

## Interpretation

- **Rule-based reading, no model** (default): controller text built from interval positions,
  with alternative explanations, unknowns and a proposed repeat experiment with a current
  audience. It passes the same contract as the model.
- **Live model** (only with `PROOFDESK_ANALYSIS_LIVE_PLAN` and the controller credential; see
  [inference.md](inference.md)): the model receives the metrics and limitations, never raw rows,
  credentials or contacts. Its JSON must cite numbers only through `[metric:ID]` placeholders;
  raw digits, percentages, currency symbols, ROI/profit/guarantee wording, unknown ids and any
  action that contacts the historical records are refused with a sanitized diagnostic. Rendering
  substitutes validated values in code. A failed live step keeps the statistical result and is
  shown as failed; nothing is substituted. These checks are lexical; they do not establish that an
  interpretation is right. No successful live analysis response has been observed yet.

## Revenue and business value

Measured historical spend and the estimated incremental historical spend per assigned customer
(with its bootstrap interval) are displayed as measurements of the 2008 campaign, never as
SalesDesk revenue or profit. A scenario (`statistics.project_scenario`) appears only when the
user enters audience size, gross margin and campaign cost: projected incremental revenue =
incremental spend per customer × audience; projected contribution = revenue × margin − cost; ROI
= contribution ÷ cost, undefined when cost is zero. Uncertainty is carried linearly from the
historical interval and the transfer assumption (a current audience behaves like the 2008
population) is disclosed. Sample size (`statistics.required_sample_size`, two-proportion pooled
normal approximation) is computed only when the minimum detectable effect, alpha and power are
entered explicitly; no conventional value is substituted. Model usage is logged per receipt
separately from the pessimistic reservation; rule-based runs are $0 model usage, not zero
infrastructure cost.

## Tasks, approvals and jobs

Tasks carry title, assignee label, source analysis, proposed action, due date, status and
completion evidence (`pending_review → approved → scheduled → running → ready_for_review →
completed`, plus `cancelled` and `failed`; transitions live in `contracts.TASK_TRANSITIONS`).
Approval binds to the proposal hash, the analysis artifact hash and the plan hash; editing the
proposal clears approvals and cancels not-yet-run preparation, and the worker re-checks the
hashes before assembling anything (`approval_stale`). Jobs (`analyze_plan`, `prepare_packet`)
record owner, plan version, approved payload hash, UTC due time, status, attempts, lease and
outcome; they are claimed atomically under a lease by the API process's scheduler thread and run
by a worker subprocess that validates its lease before every write. A lost worker is requeued
once (both kinds are deterministic) or failed; artifacts are unique per job, so duplicate dispatch
cannot create a second final artifact. A "Run now" action creates a job due immediately and takes
exactly the same path.

Packet preparation reuses the accepted interpretation with its provenance and makes no model
call. The packet binds every hash, lists readiness checks, separates entered inputs from external
prerequisites (the historical e-mail text is unavailable and must not be invented; a consented
eligibility list comes from the owner), and states what it is not: no campaign launched, no new
responses or sales, no completed review.

## What this analysis does and does not establish

An original randomized result supports a historical arm comparison under the study assumptions:
the Mens e-mail arm purchased more often than the no-e-mail arm in that population and window.
It does not establish effects of new copy, present-day audiences, individual customers,
business-to-business follow-ups or future SalesDesk revenue. Third-arm comparisons and subgroup
cells are exploratory. Repeating the analysis on a static dataset reproduces the same artifact;
it does not acquire fresh evidence.
