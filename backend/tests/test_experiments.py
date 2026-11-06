"""Experiment workspace: ingestion, statistics, sandbox contract, jobs, tasks and API.

Offline tests use a small labelled synthetic dataset with the benchmark's schema and a
test-only host runner that executes the real analysis program in a subprocess; the
product never executes analysis on the host. Docker-enabled tests run the same program in
the real sandbox and, when the pinned file is present locally, on the genuine dataset.
"""

import csv
import io
import json
import math
import os
import subprocess
import sys
import tarfile
import time
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.execution.artifacts import Rejected, sha256
from backend.app.execution.controller import (
    ANALYSIS_INPUT_BYTES,
    ANALYSIS_LIMITS,
    docker_runner,
    execute,
    serial_lock,
)
from backend.app.execution.runner import Execution, RunError, Task
from backend.app.experiments import statistics as stats
from backend.app.experiments.contracts import (
    analysis_contract,
    derive_metrics,
    format_metric,
    plan_hash,
    render_text,
    validate_plan_spec,
    validate_proposal,
    validate_result,
)
from backend.app.experiments.ingestion import (
    CHANNELS,
    COLUMNS,
    HILLSTROM,
    HISTORY_SEGMENTS,
    ZIP_CODES,
    DatasetSource,
    import_dataset,
)
from backend.app.experiments.jobs import PROGRAM_PATH, analysis_task_input, program_sha256, run_job
from backend.app.experiments.reasoning import deterministic_reading
from backend.app.experiments.service import Experiments
from backend.app.experiments.store import Store
from backend.app.generation.provider import (
    Authorization,
    Budget,
    FakeProvider,
    ModelConfig,
    fake_response,
)
from backend.app.main import create_app
from backend.app.sales.contracts import ContractError
from backend.tests.test_execution import VALIDATOR

REAL_DATASET = Path(".local/data-research/hillstrom/hillstrom.csv")
PLAN = {
    "dataset_id": "synthetic-fixture",
    "title": "Mens e-mail versus no e-mail (synthetic test fixture)",
    "question": "Did these e-mails create additional purchases?",
    "comparison": {"treatment": "mens_email", "control": "no_email"},
    "bootstrap": {"seed": 7, "resamples": 1000},
    "exploratory_breakdowns": ["newbie", "channel"],
}


def synthetic_rows():
    """Labelled synthetic rows in the benchmark schema; never user-facing evidence."""
    specs = {
        "No E-Mail": [(1, 2000), (1, 3550), (1, 0), (1, 0)] + [(0, 0)] * 16,
        "Mens E-Mail": [(1, 1000), (1, 2550), (1, 10000), (1, 525), (1, 0), (1, 0), (1, 0)]
        + [(0, 0)] * 13,
        "Womens E-Mail": [(1, 1500), (1, 4000), (1, 999), (1, 0), (1, 0)] + [(0, 0)] * 15,
    }
    rows = []
    for segment, outcomes in specs.items():
        for index, (visit, spend) in enumerate(outcomes):
            rows.append(
                [
                    str(index % 12 + 1),
                    HISTORY_SEGMENTS[index % 7],
                    "100.00",
                    str(index % 2),
                    str((index + 1) % 2),
                    ZIP_CODES[index % 3],
                    str(index % 2),
                    list(CHANNELS)[index % 3],
                    segment,
                    str(visit),
                    "1" if spend else "0",
                    f"{spend // 100}.{spend % 100:02d}" if spend else "0",
                ]
            )
    rows[19] = list(rows[18])  # Two equal-valued customers; multiplicity must be kept.
    return rows


def synthetic_csv(rows=None):
    rows = rows or synthetic_rows()
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(COLUMNS)
    writer.writerows(rows)
    return buffer.getvalue().encode()


def synthetic_source(raw, rows=60):
    return DatasetSource(
        id="synthetic-fixture",
        title="Synthetic test fixture in the Hillstrom schema",
        publisher="SalesDesk tests",
        download_url="http://synthetic.invalid/fixture.csv",
        description_url="https://synthetic.invalid/",
        catalog_url="https://synthetic.invalid/",
        checksum_reference_url="https://synthetic.invalid/",
        sha256=sha256(raw),
        bytes=len(raw),
        rows=rows,
        study_period="synthetic",
        rights="synthetic test data",
        synthetic=True,
        limitations=("Synthetic fixture for automated tests only.",),
    )


def archive_of(path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        member = tarfile.TarInfo("out/result.json")
        data = path.read_bytes()
        member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


class ProgramRunner:
    """TEST ONLY: runs the real analysis program on the host in a subprocess.

    The product executes it exclusively in the Docker sandbox. Outcomes inject failures:
    'interrupt' raises KeyboardInterrupt mid-execution, 'timeout' raises the sandbox
    deadline error, 'tamper' alters a count in the produced result before validation.
    """

    def __init__(self, outcomes=(), *, cleanup_ok=True):
        self.outcomes = iter(outcomes)
        self.cleanup_ok = cleanup_ok
        self.tasks = []
        self.evidence = {}

    def check_ready(self):
        pass

    def execute(self, name, task, limits):
        self.tasks.append(task)
        self.evidence = {"runner": "host_subprocess_test_only", "container_name": name}
        outcome = next(self.outcomes, "success")
        if outcome == "interrupt_dirty":
            self.cleanup_ok = False  # The container outlives the terminated worker.
            raise KeyboardInterrupt
        if outcome == "interrupt":
            raise KeyboardInterrupt
        if outcome == "timeout":
            raise RunError("task_deadline_exceeded")
        with TemporaryDirectory() as temp:
            work = Path(temp)
            (work / "input.txt").write_bytes(task.input)
            script = work / "script.py"
            script.write_bytes(task.script)
            process = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; exec(compile(open(sys.argv[1]).read(), '<sandbox-task>', "
                    "'exec'), {'__name__': '__main__'})",
                    str(script),
                ],
                env={"SALESDESK_WORK": str(work), "PATH": os.environ.get("PATH", "")},
                capture_output=True,
                timeout=60,
                check=False,
            )
            self.evidence["task_exit_code"] = process.returncode
            result = work / "out" / "result.json"
            if process.returncode or not result.is_file():
                return Execution(
                    process.returncode or 1, process.stdout + process.stderr, b"", self.evidence
                )
            if outcome == "tamper":
                data = json.loads(result.read_text())
                data["arms"]["no_email"]["conversions"] += 1
                result.write_text(json.dumps(data, sort_keys=True))
            return Execution(0, process.stdout + process.stderr, archive_of(result), self.evidence)

    def cleanup(self, name):
        return {"removed": self.cleanup_ok, "reason": None if self.cleanup_ok else "injected"}


def workspace(
    root, *, public_demo=False, runner_factory=None, provider=None, authorization=None, recover=None
):
    """Store with the synthetic dataset imported and an in-process job launcher."""
    store = Store(root / "experiments")
    raw = synthetic_csv()
    path = root / "fixture.csv"
    path.write_bytes(raw)
    store.save_dataset(import_dataset(path, synthetic_source(raw), store.root))
    executions = root / "executions"
    service = Experiments(
        store,
        public_demo=public_demo,
        execution_store=executions,
        scheduler_interval=0.2,
        recover=recover,
        launch=lambda job_id, token: run_job(
            store,
            job_id,
            token,
            runner=(runner_factory or ProgramRunner)(),
            execution_store=executions,
            provider=provider,
            authorization=authorization,
            ledgers=root / "ledgers",
        ),
    )
    return store, service


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def import_raw(self, raw, source=None):
        path = self.root / "fixture.csv"
        path.write_bytes(raw)
        return import_dataset(path, source or synthetic_source(raw), self.root / "store")

    def test_synthetic_fixture_imports_exact_counts_and_keeps_duplicates(self):
        manifest = self.import_raw(synthetic_csv())
        arms = {arm["id"]: arm for arm in manifest["arms"]}
        self.assertEqual(
            (arms["no_email"]["n"], arms["no_email"]["visits"], arms["no_email"]["conversions"]),
            (20, 4, 2),
        )
        self.assertEqual(arms["no_email"]["spend_cents"], 5550)
        self.assertEqual(arms["mens_email"]["spend_cents"], 14075)
        self.assertEqual(arms["mens_email"]["conversions"], 4)
        self.assertEqual(arms["womens_email"]["spend_usd"], "64.99")
        self.assertTrue(manifest["synthetic"])
        self.assertEqual(manifest["validation"]["rejections"], 0)
        derived = (self.root / "store" / manifest["analysis_input"]["path"]).read_bytes()
        self.assertEqual(sha256(derived), manifest["analysis_input"]["sha256"])
        self.assertEqual(len(derived.decode().strip().split("\n")), 61)

    def test_checksum_size_header_domain_and_value_rejections(self):
        raw = synthetic_csv()
        source = synthetic_source(raw)
        with self.assertRaisesRegex(RunError, "dataset_checksum_mismatch"):
            self.import_raw(raw.replace(b"Rural", b"Urban", 1), source)
        with self.assertRaisesRegex(RunError, "dataset_size_mismatch"):
            self.import_raw(raw + b"\n", source)
        with self.assertRaisesRegex(RunError, "dataset_header_rejected"):
            self.import_raw(raw.replace(b"recency,", b"recent,", 1))
        rows = synthetic_rows()
        rows[3][8] = "Random Policy"
        with self.assertRaisesRegex(RunError, "dataset_value_rejected") as caught:
            self.import_raw(synthetic_csv(rows))
        self.assertEqual(caught.exception.detail["column"], "segment")
        for value, column in (
            ("NaN", "spend"),
            ("inf", "spend"),
            ("-1", "spend"),
            ("1.234", "spend"),
        ):
            rows = synthetic_rows()
            rows[5][11] = value
            with self.assertRaisesRegex(RunError, "dataset_value_rejected") as caught:
                self.import_raw(synthetic_csv(rows))
            self.assertEqual(caught.exception.detail["column"], column)
        rows = synthetic_rows()
        rows[7][10] = "2"
        with self.assertRaisesRegex(RunError, "dataset_value_rejected") as caught:
            self.import_raw(synthetic_csv(rows))
        self.assertEqual(caught.exception.detail["observed"], "not_binary")
        rows = synthetic_rows()
        rows[9][2] = ""
        with self.assertRaisesRegex(RunError, "dataset_value_rejected") as caught:
            self.import_raw(synthetic_csv(rows))
        self.assertEqual(caught.exception.detail["observed"], "missing")
        rows = synthetic_rows()
        rows[1][0] = "13"
        with self.assertRaisesRegex(RunError, "dataset_value_rejected"):
            self.import_raw(synthetic_csv(rows))
        rows = synthetic_rows()[:-1]
        with self.assertRaisesRegex(RunError, "dataset_row_count_mismatch"):
            self.import_raw(synthetic_csv(rows), synthetic_source(synthetic_csv(rows)))

    @unittest.skipUnless(REAL_DATASET.is_file(), "pinned dataset cached locally")
    def test_pinned_dataset_imports_with_documented_arm_counts(self):
        manifest = import_dataset(REAL_DATASET, HILLSTROM, self.root / "store")
        arms = {arm["id"]: arm for arm in manifest["arms"]}
        self.assertEqual(manifest["raw"]["sha256"], HILLSTROM.sha256)
        self.assertEqual(manifest["raw"]["rows"], 64000)
        self.assertEqual((arms["mens_email"]["n"], arms["mens_email"]["visits"]), (21307, 3894))
        self.assertEqual(
            (arms["mens_email"]["conversions"], arms["mens_email"]["spend_usd"]), (267, "30311.69")
        )
        self.assertEqual(
            (arms["womens_email"]["n"], arms["womens_email"]["conversions"]), (21387, 189)
        )
        self.assertEqual(arms["womens_email"]["spend_usd"], "23038.11")
        self.assertEqual((arms["no_email"]["n"], arms["no_email"]["visits"]), (21306, 2262))
        self.assertEqual(
            (arms["no_email"]["conversions"], arms["no_email"]["spend_usd"]), (122, "13908.33")
        )
        self.assertFalse(manifest["synthetic"])


class StatisticsTests(unittest.TestCase):
    def test_newcombe_hybrid_score_matches_published_cases(self):
        # Newcombe (1998), Table II, method 10, to four decimals.
        cases = {
            (56, 70, 48, 80): (0.0524, 0.3339),
            (9, 10, 3, 10): (0.1705, 0.8090),
            (6, 7, 2, 7): (0.0582, 0.8062),
            (5, 56, 0, 29): (-0.0381, 0.1926),
            (0, 10, 0, 20): (-0.1611, 0.2775),
            (10, 10, 0, 20): (0.6791, 1.0),
        }
        for inputs, expected in cases.items():
            low, high = stats.newcombe_difference(*inputs)
            self.assertAlmostEqual(low, expected[0], places=4)
            self.assertAlmostEqual(high, expected[1], places=4)

    def test_wilson_agrees_with_independent_score_root_finding(self):
        z = stats.Z_95
        for events, n in ((0, 10), (3, 10), (267, 21307), (122, 21306), (20, 20)):
            low, high = stats.wilson_interval(events, n)
            p = events / n

            # The Wilson bounds are the roots of (p - q)^2 = z^2 q (1 - q) / n, found by bisection.
            def score(q):
                return (p - q) ** 2 - z * z * q * (1 - q) / n

            # The root at p itself is excluded so bisection finds the other root.
            for bound, (a, b) in ((low, (0.0, p - 1e-9)), (high, (p + 1e-9, 1.0))):
                if a >= b:
                    self.assertAlmostEqual(bound, p, places=9)
                    continue
                for _ in range(200):
                    mid = (a + b) / 2
                    if score(a) * score(mid) <= 0:
                        b = mid
                    else:
                        a = mid
                self.assertAlmostEqual(bound, (a + b) / 2, places=9)

    def test_empty_groups_zero_events_and_undefined_ratios(self):
        self.assertIsNone(stats.wilson_interval(0, 0))
        self.assertIsNone(stats.newcombe_difference(0, 0, 1, 10))
        self.assertEqual(stats.wilson_interval(0, 10)[0], 0.0)
        self.assertIsNone(stats.relative_change(0.1, 0.0))
        self.assertAlmostEqual(stats.relative_change(0.2, 0.1), 1.0)
        with self.assertRaises(ValueError):
            stats.wilson_interval(11, 10)

    def test_currency_scenario_and_sample_size_inputs(self):
        self.assertEqual(stats.cents("30311.69"), 3031169)
        self.assertEqual(stats.usd(3031169), "30311.69")
        for bad in ("1.234", "-1", "NaN", "inf"):
            with self.assertRaises(ValueError):
                stats.cents(bad)
        missing = stats.project_scenario(
            77, [50, 100], {"audience_size": None, "gross_margin": 0.4, "campaign_cost_usd": "10"}
        )
        self.assertFalse(missing["available"])
        self.assertEqual(missing["missing_inputs"], ["audience_size"])
        zero_cost = stats.project_scenario(
            77, [50, 100], {"audience_size": 1000, "gross_margin": 0.5, "campaign_cost_usd": "0"}
        )
        self.assertIsNone(zero_cost["projected_roi"])
        self.assertIn("undefined", zero_cost["roi_note"])
        self.assertEqual(zero_cost["projected_contribution_usd"], "385.00")
        projected = stats.project_scenario(
            77,
            [50, 100],
            {"audience_size": 1000, "gross_margin": 0.5, "campaign_cost_usd": "100.00"},
        )
        self.assertEqual(projected["projected_contribution_interval_usd"], ["150.00", "400.00"])
        self.assertAlmostEqual(projected["projected_roi"], 2.85)
        self.assertEqual(projected["label"], "scenario_assumption_not_measurement")
        with self.assertRaises(ValueError):
            stats.required_sample_size(0.0057, 0.5, 0.05, 0.3)
        size = stats.required_sample_size(0.0057, 0.5, 0.05, 0.8)
        self.assertGreater(size["per_arm"], 1000)
        self.assertEqual(size["total_two_arms"], 2 * size["per_arm"])


class ProgramTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        raw = synthetic_csv()
        path = self.root / "fixture.csv"
        path.write_bytes(raw)
        self.manifest = import_dataset(path, synthetic_source(raw), self.root / "store")
        self.input = (self.root / "store" / self.manifest["analysis_input"]["path"]).read_bytes()
        self.spec = validate_plan_spec(
            {k: v for k, v in PLAN.items() if k != "dataset_id"}, self.manifest
        )
        self.script = PROGRAM_PATH.read_bytes()

    def run_program(self, runner=None, spec=None):
        spec = spec or self.spec
        task_input = analysis_task_input(self.input, spec)
        digest = sha256(task_input)

        def checker(actual):
            try:
                validate_result(
                    actual,
                    manifest=self.manifest,
                    spec=spec,
                    input_sha256=digest,
                    program_sha256=program_sha256(),
                )
            except Rejected:
                raise
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                raise Rejected("analysis_result_malformed") from exc

        with serial_lock(self.root / "executions"):
            path, record = execute(
                runner or ProgramRunner(),
                Task(self.script, task_input),
                {"contract": "analysis_result_contract_v1", "plan_sha256": plan_hash(spec)},
                scenario="experiment-analysis",
                store=self.root / "executions",
                limits=ANALYSIS_LIMITS,
                validator=checker,
                validation="analysis_result_contract_v1",
                task_bytes=ANALYSIS_INPUT_BYTES,
            )
        VALIDATOR.validate(record)
        return path, record, digest

    def test_program_result_reconciles_and_is_reproducible(self):
        path, record, digest = self.run_program()
        self.assertEqual(record["status"], "succeeded", record)
        self.assertEqual(
            record["validated_artifacts"][0]["validation"], "analysis_result_contract_v1"
        )
        self.assertEqual(record["limits"]["wall_seconds"], 30)
        result = json.loads((path.parent / "result.json").read_text())
        reconciliation = validate_result(
            result,
            manifest=self.manifest,
            spec=self.spec,
            input_sha256=digest,
            program_sha256=program_sha256(),
        )
        self.assertEqual(reconciliation["status"], "matched")
        conversion = result["comparison"]["conversion"]
        self.assertEqual(
            (conversion["treatment"]["events"], conversion["control"]["events"]), (4, 2)
        )
        self.assertAlmostEqual(conversion["difference"], 0.1)
        low, high = stats.newcombe_difference(4, 20, 2, 20)
        self.assertAlmostEqual(conversion["difference_interval"][0], low)
        self.assertAlmostEqual(conversion["difference_interval"][1], high)
        spend = result["comparison"]["spend"]
        self.assertAlmostEqual(spend["difference_cents"], 14075 / 20 - 5550 / 20)
        self.assertEqual(spend["bootstrap"]["seed"], 7)
        self.assertEqual(spend["denominator"], "all assigned customers, including zero spend")
        self.assertEqual(result["exploratory"]["breakdowns"]["newbie"]["0"]["treatment"]["n"], 10)
        second, _, _ = self.run_program()
        self.assertEqual(
            (second.parent / "result.json").read_bytes(), (path.parent / "result.json").read_bytes()
        )
        metrics = derive_metrics(result, self.manifest, self.spec)
        by_id = {m["id"]: m for m in metrics}
        self.assertIn("(4 of 20)", format_metric(by_id["treatment.conversion_rate"]))
        self.assertIn("percentage points", format_metric(by_id["conversion.difference_pp"]))
        self.assertTrue(by_id["exploratory.newbie.0.treatment.conversion_rate"]["exploratory"])
        self.assertIn("source.womens_email.customers", by_id)
        self.assertIn("95% bootstrap CI", format_metric(by_id["spend.incremental_per_customer"]))

    def test_tampered_counts_timeout_and_bad_plans_leave_no_result(self):
        path, record, _ = self.run_program(ProgramRunner(["tamper"]))
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["failure_reason"], "reconciliation_mismatch_conversions")
        self.assertFalse((path.parent / "result.json").exists())
        self.assertEqual(record["validated_artifacts"], [])
        path, record, _ = self.run_program(ProgramRunner(["timeout"]))
        self.assertEqual(record["failure_reason"], "task_deadline_exceeded")
        self.assertFalse((path.parent / "result.json").exists())
        self.assertTrue(record["cleanup"]["removed"])
        # Historical assignment stays fixed: a plan can only name original arms.
        with self.assertRaisesRegex(RunError, "invalid_plan_comparison"):
            validate_plan_spec(
                {
                    **{k: v for k, v in PLAN.items() if k != "dataset_id"},
                    "comparison": {"treatment": "new_random_policy", "control": "no_email"},
                },
                self.manifest,
            )
        with self.assertRaisesRegex(RunError, "invalid_plan_comparison"):
            validate_plan_spec(
                {
                    **{k: v for k, v in PLAN.items() if k != "dataset_id"},
                    "comparison": {"treatment": "no_email", "control": "no_email"},
                },
                self.manifest,
            )
        with self.assertRaisesRegex(RunError, "invalid_plan"):
            validate_plan_spec(
                {**{k: v for k, v in PLAN.items() if k != "dataset_id"}, "reassign": True},
                self.manifest,
            )
        with self.assertRaisesRegex(RunError, "invalid_plan_bootstrap"):
            validate_plan_spec(
                {
                    **{k: v for k, v in PLAN.items() if k != "dataset_id"},
                    "bootstrap": {"seed": 1, "resamples": 5},
                },
                self.manifest,
            )
        # A changed program is bound by hash; the sandbox echoes the plan hash it was given.
        other = validate_plan_spec(
            {
                **{k: v for k, v in PLAN.items() if k != "dataset_id"},
                "bootstrap": {"seed": 8, "resamples": 1000},
            },
            self.manifest,
        )
        path, record, digest = self.run_program(spec=other)
        result = json.loads((path.parent / "result.json").read_text())
        with self.assertRaisesRegex(Rejected, "analysis_plan_hash_mismatch"):
            validate_result(
                result,
                manifest=self.manifest,
                spec=self.spec,
                input_sha256=digest,
                program_sha256=program_sha256(),
            )

    def test_oversized_input_and_script_are_rejected_before_dispatch(self):
        runner = ProgramRunner()
        with serial_lock(self.root / "executions"):
            _, record = execute(
                runner,
                Task(self.script, b"x" * (ANALYSIS_INPUT_BYTES + 1)),
                {"contract": "analysis_result_contract_v1"},
                scenario="experiment-analysis",
                store=self.root / "executions",
                limits=ANALYSIS_LIMITS,
                validator=lambda actual: None,
                validation="analysis_result_contract_v1",
                task_bytes=ANALYSIS_INPUT_BYTES,
            )
        VALIDATOR.validate(record)
        self.assertEqual(record["failure_reason"], "task_input_limit")
        self.assertEqual(record["input_rejection"]["limit"], ANALYSIS_INPUT_BYTES)
        self.assertFalse(runner.tasks)
        with self.assertRaisesRegex(RunError, "invalid_task_input_limit"):
            execute(
                runner,
                Task(b"", b""),
                {},
                scenario="x",
                store=self.root / "executions",
                task_bytes=10 * ANALYSIS_INPUT_BYTES,
            )
        with self.assertRaisesRegex(RunError, "invalid_validation_contract"):
            execute(
                runner,
                Task(b"", b""),
                {},
                scenario="x",
                store=self.root / "executions",
                validator=lambda a: None,
            )


class AnalysisContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        raw = synthetic_csv()
        path = root / "fixture.csv"
        path.write_bytes(raw)
        manifest = import_dataset(path, synthetic_source(raw), root / "store")
        self.spec = validate_plan_spec(
            {k: v for k, v in PLAN.items() if k != "dataset_id"}, manifest
        )
        task_input = analysis_task_input(
            (root / "store" / manifest["analysis_input"]["path"]).read_bytes(), self.spec
        )
        with serial_lock(root / "executions"):
            path, record = execute(
                ProgramRunner(),
                Task(PROGRAM_PATH.read_bytes(), task_input),
                {"contract": "analysis_result_contract_v1"},
                scenario="experiment-analysis",
                store=root / "executions",
                limits=ANALYSIS_LIMITS,
                validator=lambda actual: None,
                validation="analysis_result_contract_v1",
                task_bytes=ANALYSIS_INPUT_BYTES,
            )
        self.result = json.loads((path.parent / "result.json").read_text())
        self.metrics = derive_metrics(self.result, manifest, self.spec)
        self.by_id = {m["id"]: m for m in self.metrics}

    def reading(self, **changes):
        base = {
            k: v
            for k, v in deterministic_reading(self.metrics, self.spec).items()
            if k != "metric_ids_used"
        }
        for key, value in changes.items():
            if key.startswith("next."):
                base["proposed_next_experiment"][key[5:]] = value
            else:
                base[key] = value
        return json.dumps(base)

    def diagnostic(self, content):
        with self.assertRaises(ContractError) as caught:
            analysis_contract(content, self.metrics)
        return caught.exception.diagnostic

    def test_deterministic_reading_passes_and_renders_only_validated_values(self):
        validated = analysis_contract(self.reading(), self.metrics)
        self.assertIn("conversion.difference_pp", validated["metric_ids_used"])
        rendered = render_text(validated["interpretation"], self.by_id)
        self.assertNotIn("[metric:", rendered)
        self.assertIn("(4 of 20)", rendered)
        with self.assertRaisesRegex(RunError, "unknown_metric_id"):
            render_text("[metric:not.a.metric]", self.by_id)

    def test_unknown_metrics_raw_numbers_roi_and_contact_actions_are_rejected(self):
        self.assertEqual(
            self.diagnostic(self.reading(interpretation="See [metric:made.up]."))["observed"],
            "unknown_metric_id",
        )
        self.assertEqual(
            self.diagnostic(self.reading(interpretation="Purchases rose 0.68 points."))["observed"],
            "unsupported_quantity",
        )
        self.assertEqual(
            self.diagnostic(self.reading(interpretation="Rates rose by five percent %."))[
                "observed"
            ],
            "unsupported_quantity",
        )
        self.assertEqual(
            self.diagnostic(
                self.reading(interpretation="This e-mail is profitable with strong ROI.")
            )["observed"],
            "invented_roi_or_outcome",
        )
        self.assertEqual(
            self.diagnostic(
                self.reading(**{"next.variant_a": "Re-email these customers from the dataset."})
            )["observed"],
            "unauthorized_action",
        )
        self.assertEqual(
            self.diagnostic(
                self.reading(
                    **{"next.decision_rule": "Target the historical records with a new offer."}
                )
            )["observed"],
            "unauthorized_action",
        )
        self.assertEqual(
            self.diagnostic(self.reading(alternative_explanations=[]))["expected"], "array of 1..6"
        )
        self.assertEqual(self.diagnostic('{"interpretation": "x"}')["observed"], "keys_mismatch")
        self.assertEqual(self.diagnostic("not json")["observed"], "unparseable")
        self.assertEqual(
            self.diagnostic(self.reading(proposed_next_experiment={"hypothesis": "x"}))["field"],
            "proposed_next_experiment",
        )
        accepted = analysis_contract(
            self.reading(
                **{
                    "next.variant_a": (
                        "Send the e-mail to a current customer audience with a holdout."
                    )
                }
            ),
            self.metrics,
        )
        self.assertIn(
            "current customer audience", accepted["proposed_next_experiment"]["variant_a"]
        )

    def test_proposal_validation_bounds_inputs(self):
        content = deterministic_reading(self.metrics, self.spec)["proposed_next_experiment"]
        base = {
            **content,
            "scenario_assumptions": {
                "audience_size": 1000,
                "gross_margin": 0.4,
                "campaign_cost_usd": "250.00",
            },
            "sample_size_inputs": {"minimum_detectable_pp": 0.5, "alpha": 0.05, "power": 0.8},
            "notes": "",
        }
        validated = validate_proposal(base)
        self.assertEqual(validated["scenario_assumptions"]["campaign_cost_usd"], "250.00")
        for field, value in (
            ("audience_size", 0),
            ("gross_margin", 1.5),
            ("campaign_cost_usd", "1e3"),
        ):
            with self.assertRaises(RunError):
                validate_proposal(
                    {**base, "scenario_assumptions": {**base["scenario_assumptions"], field: value}}
                )
        with self.assertRaisesRegex(RunError, "invalid_power"):
            validate_proposal(
                {**base, "sample_size_inputs": {**base["sample_size_inputs"], "power": 0.1}}
            )
        with self.assertRaisesRegex(RunError, "invalid_proposal"):
            validate_proposal({**base, "launch": True})


class WorkflowTests(unittest.TestCase):
    OWNER = "owner-a"

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store, self.service = workspace(self.root)
        self.addCleanup(self.service.stop)

    def plan(self, owner=OWNER, **changes):
        return self.service.create_plan(owner, uuid.uuid4().hex, {**PLAN, **changes})

    def run_plan(self, plan_id, owner=OWNER):
        job = self.service.run_now(plan_id, owner, uuid.uuid4().hex)
        self.assertEqual(job["status"], "scheduled")
        claimed = self.service.scheduler.tick()
        self.assertEqual(claimed["id"], job["id"])
        return self.service.job_detail(job["id"], owner)

    def proposal_body(self, detail, **changes):
        content = dict(detail["proposals"][0]["content"])
        content.update(changes)
        return content

    def test_journey_from_plan_to_reviewed_packet(self):
        plan = self.plan()
        self.assertEqual(plan["version"], 1)
        job = self.run_plan(plan["id"])
        self.assertEqual(job["status"], "succeeded", job)
        self.assertEqual(job["attempts"], 1)
        detail = self.service.plan_detail(plan["id"], self.OWNER)
        run = detail["runs"][0]
        self.assertEqual(run["status"], "succeeded")
        self.assertEqual(run["reconciliation"]["status"], "matched")
        self.assertEqual(run["interpretation"]["provenance"], "deterministic")
        self.assertEqual(
            run["execution"]["validated_artifacts"][0]["validation"], "analysis_result_contract_v1"
        )
        self.assertIsNone(run["execution"].get("input"))
        artifact = self.service.artifact_view(run["artifact_id"], self.OWNER)
        self.assertEqual(artifact["kind"], "analysis_result")
        self.assertEqual(artifact["content"]["plan_sha256"], plan["sha256"])
        self.assertEqual(run["generation"]["mode"], "deterministic")
        self.assertEqual(run["generation"]["receipts"], {})
        # A proposal was derived from the labelled rule-based reading.
        self.assertEqual(detail["proposals"][0]["version"], 1)
        self.assertEqual(detail["proposals"][0]["provenance"], "deterministic")
        # Reproducibility: a second run yields the identical artifact bytes.
        self.run_plan(plan["id"])
        detail = self.service.plan_detail(plan["id"], self.OWNER)
        hashes = {
            self.service.artifact_view(r["artifact_id"], self.OWNER)["sha256"]
            for r in detail["runs"]
        }
        self.assertEqual(len(detail["runs"]), 2)
        self.assertEqual(len(hashes), 1)
        # Edit the proposal with scenario assumptions: new version.
        edited = self.service.save_proposal(
            plan["id"],
            self.OWNER,
            uuid.uuid4().hex,
            self.proposal_body(
                detail,
                scenario_assumptions={
                    "audience_size": 50000,
                    "gross_margin": 0.4,
                    "campaign_cost_usd": "1200.00",
                },
                sample_size_inputs={"minimum_detectable_pp": 0.5, "alpha": 0.05, "power": 0.8},
                notes="Reviewed by the sales manager.",
            ),
            base_version=1,
        )
        self.assertEqual((edited["version"], edited["provenance"]), (2, "human_edited"))
        with self.assertRaisesRegex(RunError, "proposal_version_conflict"):
            self.service.save_proposal(
                plan["id"], self.OWNER, uuid.uuid4().hex, self.proposal_body(detail), base_version=1
            )
        task = self.service.create_task(
            plan["id"],
            self.OWNER,
            uuid.uuid4().hex,
            {
                "title": "Review the repeat experiment packet",
                "assignee_label": "Sales manager",
                "proposed_action": "Review and decide",
                "due_date": "2026-11-12",
            },
        )
        self.assertEqual((task["status"], task["proposal_version"]), ("pending_review", 2))
        with self.assertRaisesRegex(RunError, "task_not_approved"):
            self.service.schedule_task(task["id"], self.OWNER, uuid.uuid4().hex, due_at="now")
        with self.assertRaisesRegex(RunError, "proposal_version_conflict"):
            self.service.approve_task(
                task["id"], self.OWNER, uuid.uuid4().hex, proposal_sha256="0" * 64
            )
        approved = self.service.approve_task(
            task["id"], self.OWNER, uuid.uuid4().hex, proposal_sha256=edited["sha256"]
        )
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["approval"]["artifact_sha256"], hashes.pop())
        scheduled = self.service.schedule_task(
            task["id"], self.OWNER, uuid.uuid4().hex, due_at="now"
        )
        self.assertEqual(scheduled["status"], "scheduled")
        job = self.service.job_detail(scheduled["job_id"], self.OWNER)
        self.assertEqual((job["kind"], job["status"]), ("prepare_packet", "scheduled"))
        with self.assertRaisesRegex(RunError, "packet_not_ready"):
            self.service.complete_task(task["id"], self.OWNER, uuid.uuid4().hex, evidence_note="x")
        claimed = self.service.scheduler.tick()
        self.assertEqual(claimed["id"], job["id"])
        job = self.service.job_detail(job["id"], self.OWNER)
        self.assertEqual(job["status"], "succeeded", job)
        self.assertFalse(job["outcome"]["model_call"])
        task = self.service.plan_detail(plan["id"], self.OWNER)["tasks"][0]
        self.assertEqual(task["status"], "ready_for_review")
        packet, meta = self.service.packet_markdown(task["packet_artifact_id"], self.OWNER)
        self.assertIn("# Experiment packet", packet)
        self.assertIn("Projected contribution", packet)
        content = meta["content"]["packet"]
        self.assertEqual(content["status"], "inputs_complete_pending_human_launch_decision")
        self.assertEqual(content["bindings"]["proposal_sha256"], edited["sha256"])
        self.assertTrue(content["scenario"]["available"])
        self.assertEqual(content["unresolved_inputs"], [])
        self.assertIn("historical_email_text", content["external_prerequisites"])
        self.assertIn("No campaign was launched", content["not_claimed"][0])
        self.assertTrue(content["sample_size"]["per_arm"] > 0)
        completed = self.service.complete_task(
            task["id"],
            self.OWNER,
            uuid.uuid4().hex,
            evidence_note="Reviewed the packet; audience list still pending.",
        )
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(
            [e["stage"] for e in completed["events"]],
            ["pending_review", "approved", "scheduled", "running", "ready_for_review", "completed"],
        )
        overview = self.service.overview(self.OWNER)
        self.assertEqual(overview["plans"][0]["tasks"], ["completed"])
        self.assertEqual(overview["plans"][0]["runs"], 2)

    def test_missing_inputs_leave_packet_at_planning_review(self):
        plan = self.plan()
        self.run_plan(plan["id"])
        detail = self.service.plan_detail(plan["id"], self.OWNER)
        proposal = detail["proposals"][0]
        task = self.service.create_task(
            plan["id"],
            self.OWNER,
            uuid.uuid4().hex,
            {
                "title": "Plan",
                "assignee_label": "Owner",
                "proposed_action": "Review",
                "due_date": None,
            },
        )
        self.service.approve_task(
            task["id"], self.OWNER, uuid.uuid4().hex, proposal_sha256=proposal["sha256"]
        )
        self.service.schedule_task(task["id"], self.OWNER, uuid.uuid4().hex, due_at="now")
        self.service.scheduler.tick()
        task = self.service.plan_detail(plan["id"], self.OWNER)["tasks"][0]
        self.assertEqual(task["status"], "ready_for_review")
        packet = self.service.artifact_view(task["packet_artifact_id"], self.OWNER)["content"][
            "packet"
        ]
        self.assertEqual(packet["status"], "planning_review")
        self.assertFalse(packet["scenario"]["available"])
        self.assertIn("audience_size", packet["unresolved_inputs"])
        self.assertFalse(packet["sample_size"].get("per_arm"))

    def test_editing_after_approval_invalidates_and_worker_refuses_stale_approval(self):
        plan = self.plan()
        self.run_plan(plan["id"])
        detail = self.service.plan_detail(plan["id"], self.OWNER)
        proposal = detail["proposals"][0]
        task = self.service.create_task(
            plan["id"],
            self.OWNER,
            uuid.uuid4().hex,
            {
                "title": "Plan",
                "assignee_label": "Owner",
                "proposed_action": "Review",
                "due_date": None,
            },
        )
        self.service.approve_task(
            task["id"], self.OWNER, uuid.uuid4().hex, proposal_sha256=proposal["sha256"]
        )
        scheduled = self.service.schedule_task(
            task["id"], self.OWNER, uuid.uuid4().hex, due_at="now"
        )
        self.service.save_proposal(
            plan["id"],
            self.OWNER,
            uuid.uuid4().hex,
            self.proposal_body(detail, notes="changed"),
            base_version=1,
        )
        task = self.service.plan_detail(plan["id"], self.OWNER)["tasks"][0]
        self.assertEqual(task["status"], "pending_review")
        self.assertIsNone(task["approval"])
        self.assertEqual(
            self.service.job_detail(scheduled["job_id"], self.OWNER)["status"], "cancelled"
        )
        self.assertIsNone(self.service.scheduler.tick())
        # Approve the new version, schedule, then tamper with the approval hash behind the job.
        proposal = self.service.plan_detail(plan["id"], self.OWNER)["proposals"][0]
        self.service.approve_task(
            task["id"], self.OWNER, uuid.uuid4().hex, proposal_sha256=proposal["sha256"]
        )
        scheduled = self.service.schedule_task(
            task["id"], self.OWNER, uuid.uuid4().hex, due_at="now"
        )
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE tasks SET approval = json_set(approval, '$.sha256', ?) WHERE id = ?",
                ("0" * 64, task["id"]),
            )
        self.service.scheduler.tick()
        job = self.service.job_detail(scheduled["job_id"], self.OWNER)
        self.assertEqual((job["status"], job["failure_reason"]), ("failed", "approval_stale"))
        self.assertEqual(
            self.service.plan_detail(plan["id"], self.OWNER)["tasks"][0]["status"], "failed"
        )
        with self.store.reading() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE kind = 'experiment_packet'"
                ).fetchone()[0],
                0,
            )

    def test_duplicate_dispatch_and_lost_lease_cannot_duplicate_results(self):
        plan = self.plan()
        job = self.service.run_now(plan["id"], self.OWNER, uuid.uuid4().hex)
        same = self.service.run_now(plan["id"], self.OWNER, job["operation_key"].split(":")[-1])
        self.assertEqual(same["id"], job["id"])
        with self.store.transaction() as conn:
            claimed = self.store.claim_due(conn, datetime.now(UTC).isoformat(), "token-a", 120)
            self.assertEqual(claimed["id"], job["id"])
            self.assertIsNone(
                self.store.claim_due(conn, datetime.now(UTC).isoformat(), "token-b", 120)
            )
        run_job(
            self.store,
            job["id"],
            "token-a",
            runner=ProgramRunner(),
            execution_store=self.root / "executions",
        )
        with self.store.reading() as conn:
            self.assertEqual(self.store.job(conn, job["id"])["status"], "succeeded")
        # A late duplicate worker with the old token cannot write anything.
        run_job(
            self.store,
            job["id"],
            "token-a",
            runner=ProgramRunner(),
            execution_store=self.root / "executions",
        )
        with self.store.reading() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0], 1)
            with self.assertRaisesRegex(RunError, "artifact_already_saved"):
                self.store.save_artifact(
                    conn, owner=self.OWNER, kind="analysis_result", content=b"{}", job_id=job["id"]
                )
        # An expired lease requeues once; the stale token is refused afterwards.
        second = self.service.run_now(plan["id"], self.OWNER, uuid.uuid4().hex)
        with self.store.transaction() as conn:
            claimed = self.store.claim_due(conn, datetime.now(UTC).isoformat(), "token-c", 1)
            self.assertEqual(claimed["id"], second["id"])
        later = (datetime.now(UTC) + timedelta(seconds=5)).isoformat()
        with self.store.transaction() as conn:
            requeued = self.store.expire_leases(conn, later)
            self.assertEqual([j["status"] for j in requeued], ["scheduled"])
            with self.assertRaisesRegex(RunError, "job_lease_lost"):
                self.store.verify_lease(conn, second["id"], "token-c")
        run_job(
            self.store,
            second["id"],
            "token-c",
            runner=ProgramRunner(),
            execution_store=self.root / "executions",
        )
        with self.store.reading() as conn:
            self.assertEqual(self.store.job(conn, second["id"])["status"], "scheduled")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 1)
        self.service.scheduler.tick()
        self.assertEqual(self.service.job_detail(second["id"], self.OWNER)["status"], "succeeded")
        self.assertEqual(self.service.job_detail(second["id"], self.OWNER)["attempts"], 2)

    def test_interrupted_worker_requeues_once_and_restart_completes(self):
        outcomes = iter(
            [
                ProgramRunner(["interrupt"]),
                ProgramRunner(),
                ProgramRunner(["interrupt"]),
                ProgramRunner(["interrupt"]),
            ]
        )
        self.store, self.service = workspace(
            self.root / "second", runner_factory=lambda: next(outcomes)
        )
        self.addCleanup(self.service.stop)
        plan = self.plan()
        job = self.service.run_now(plan["id"], self.OWNER, uuid.uuid4().hex)
        self.service.scheduler.tick()
        saved = self.service.job_detail(job["id"], self.OWNER)
        self.assertEqual((saved["status"], saved["attempts"]), ("scheduled", 1))
        self.assertIn("interrupted_requeued", [e["stage"] for e in saved["events"]])
        self.service.scheduler.tick()
        saved = self.service.job_detail(job["id"], self.OWNER)
        self.assertEqual((saved["status"], saved["attempts"]), ("succeeded", 2))
        runs = self.service.plan_detail(plan["id"], self.OWNER)["runs"]
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "succeeded")
        # Two interruptions exhaust the bounded retry.
        job = self.service.run_now(plan["id"], self.OWNER, uuid.uuid4().hex)
        self.service.scheduler.tick()
        self.service.scheduler.tick()
        saved = self.service.job_detail(job["id"], self.OWNER)
        self.assertEqual(
            (saved["status"], saved["failure_reason"]), ("failed", "controller_interrupted")
        )
        # A worker terminated while its container could not be removed still requeues; the
        # restarted API's startup recovery runs before the next dispatch.
        recoveries = []
        dirty = iter([ProgramRunner(["interrupt_dirty"]), ProgramRunner()])
        self.store, self.service = workspace(
            self.root / "dirty",
            runner_factory=lambda: next(dirty),
            recover=lambda: recoveries.append("recovered") or {"removed_containers": ["x"]},
        )
        self.addCleanup(self.service.stop)
        plan = self.plan()
        job = self.service.run_now(plan["id"], self.OWNER, uuid.uuid4().hex)
        self.service.scheduler.tick()
        saved = self.service.job_detail(job["id"], self.OWNER)
        self.assertEqual((saved["status"], saved["attempts"]), ("scheduled", 1))
        self.assertEqual(recoveries, [])
        self.service.reconcile()  # The lifespan hook of a restarted API.
        self.assertEqual(recoveries, ["recovered"])
        self.assertEqual(
            self.service.overview(self.OWNER)["scheduler"]["last_recovery"],
            {"removed_containers": ["x"]},
        )
        self.service.scheduler.tick()
        self.assertEqual(self.service.job_detail(job["id"], self.OWNER)["status"], "succeeded")
        # A restarted scheduler with a job stuck in 'running' requeues it rather than losing it.
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'running', attempts = 1, lease_token = 'dead',"
                " lease_until = ? WHERE id = ?",
                ((datetime.now(UTC) + timedelta(minutes=5)).isoformat(), job["id"]),
            )
        self.service.reconcile()
        self.assertEqual(self.service.job_detail(job["id"], self.OWNER)["status"], "scheduled")

    def test_cancellation_quotas_public_limits_and_cross_owner_isolation(self):
        plan = self.plan()
        self.run_plan(plan["id"])
        detail = self.service.plan_detail(plan["id"], self.OWNER)
        task = self.service.create_task(
            plan["id"],
            self.OWNER,
            uuid.uuid4().hex,
            {
                "title": "Plan",
                "assignee_label": "Owner",
                "proposed_action": "Review",
                "due_date": None,
            },
        )
        self.service.approve_task(
            task["id"],
            self.OWNER,
            uuid.uuid4().hex,
            proposal_sha256=detail["proposals"][0]["sha256"],
        )
        with self.assertRaisesRegex(RunError, "due_at_out_of_range"):
            self.service.schedule_task(
                task["id"], self.OWNER, uuid.uuid4().hex, due_at="2030-01-01T00:00:00+00:00"
            )
        with self.assertRaisesRegex(RunError, "invalid_due_at"):
            self.service.schedule_task(
                task["id"], self.OWNER, uuid.uuid4().hex, due_at="2026-11-06 10:00"
            )
        future = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
        scheduled = self.service.schedule_task(
            task["id"], self.OWNER, uuid.uuid4().hex, due_at=future
        )
        self.assertIsNone(self.service.scheduler.tick())  # Not due yet.
        self.service.cancel_task(task["id"], self.OWNER)
        self.assertEqual(
            self.service.job_detail(scheduled["job_id"], self.OWNER)["status"], "cancelled"
        )
        with self.assertRaisesRegex(RunError, "task_not_approved"):
            self.service.schedule_task(task["id"], self.OWNER, uuid.uuid4().hex, due_at="now")
        for other in ("plan_detail", "job_detail"):
            with self.assertRaisesRegex(RunError, "experiment_not_found"):
                getattr(self.service, other)(
                    plan["id"] if other == "plan_detail" else scheduled["job_id"], "owner-b"
                )
        with self.assertRaisesRegex(RunError, "experiment_not_found"):
            self.service.artifact_view(detail["runs"][0]["artifact_id"], "owner-b")
        with self.assertRaisesRegex(RunError, "experiment_not_found"):
            self.service.cancel_task(task["id"], "owner-b")
        self.assertEqual(self.service.overview("owner-b")["plans"], [])
        # Public mode: small quotas and a short due horizon.
        store, public = workspace(self.root / "public", public_demo=True)
        self.addCleanup(public.stop)
        for _ in range(3):
            public.create_plan("visitor", uuid.uuid4().hex, PLAN)
        with self.assertRaisesRegex(RunError, "experiment_quota_reached"):
            public.create_plan("visitor", uuid.uuid4().hex, PLAN)
        plan_id = public.overview("visitor")["plans"][0]["id"]
        for _ in range(3):
            public.run_now(plan_id, "visitor", uuid.uuid4().hex)
        with self.assertRaisesRegex(RunError, "experiment_queue_full"):
            public.run_now(plan_id, "visitor", uuid.uuid4().hex)
        self.assertEqual(public.limits["due_horizon_seconds"], 86400)

    def test_live_interpretation_failure_preserves_result_and_success_is_labelled(self):
        config = ModelConfig(
            "qwen3.8-flash-next",
            deadline_seconds=60,
            max_input_tokens=16000,
            max_output_tokens=2048,
        )
        budget = Budget(
            max_requests=2,
            max_total_tokens=40000,
            ceiling_usd="0.01",
            input_usd_per_million="0.10",
            output_usd_per_million="0.20",
        )
        authorization = Authorization(
            config,
            budget,
            "synthetic-approval",
            "https://api.vultrinference.com/v1/models",
            "2026-11-05",
        )
        good = {
            "question_answered": (
                "Did the [metric:design.treatment_label] e-mail create additional purchases?"
            ),
            "interpretation": (
                "Purchases were [metric:treatment.conversion_rate] versus "
                "[metric:control.conversion_rate], a difference of "
                "[metric:conversion.difference_pp]."
            ),
            "alternative_explanations": ["Chance within the reported interval."],
            "unknowns": ["Campaign cost and margin are not recorded."],
            "proposed_next_experiment": {
                "hypothesis": (
                    "A comparable e-mail to a current audience raises purchases within two weeks."
                ),
                "variant_a": "Send to consenting current customers.",
                "variant_b": "Random holdout receives nothing.",
                "audience_requirements": ["Current customers with consent."],
                "unit_of_randomization": "customer",
                "primary_outcome": "purchase within the window",
                "observation_window": "fourteen days",
                "decision_rule": "Adopt only if the interval for the difference is above zero.",
                "missing_inputs": ["audience size", "cost"],
            },
        }
        provider = FakeProvider([fake_response("not json at all"), fake_response(json.dumps(good))])
        with patch.dict(
            os.environ,
            {
                "PROOFDESK_ANALYSIS_LIVE_PLAN": "plan.json",
                "VULTR_INFERENCE_API_KEY": "synthetic-sentinel",
            },
        ):
            self.store, self.service = workspace(
                self.root / "live", provider=provider, authorization=authorization
            )
            self.addCleanup(self.service.stop)
            self.assertEqual(self.service.mode(), "live_model")
            plan = self.plan()
            self.run_plan(plan["id"])
            detail = self.service.plan_detail(plan["id"], self.OWNER)
            run = detail["runs"][0]
            self.assertEqual(run["status"], "succeeded")
            self.assertEqual(run["reconciliation"]["status"], "matched")
            self.assertEqual(run["interpretation"]["status"], "failed")
            self.assertEqual(run["interpretation"]["failure_reason"], "analysis_contract_rejected")
            self.assertEqual(
                run["generation"]["diagnostics"][0]["diagnostic"]["observed"], "unparseable"
            )
            self.assertEqual(detail["proposals"], [])
            self.assertEqual(run["generation"]["budget"]["reserved_requests"], 1)
            self.run_plan(plan["id"])
            detail = self.service.plan_detail(plan["id"], self.OWNER)
            run = detail["runs"][0]
            self.assertEqual(run["interpretation"]["provenance"], "live_model")
            self.assertIn("(4 of 20)", run["interpretation"]["rendered"]["interpretation"])
            self.assertEqual(detail["proposals"][0]["provenance"], "live_model")
            self.assertEqual(run["generation"]["usage"]["analysis"]["completion_tokens"], 500)
            self.assertEqual(run["generation"]["reservation"]["analysis"]["output_tokens"], 2048)
            # The budget is exhausted: a third run keeps its statistics and reports the stop.
            self.run_plan(plan["id"])
            run = self.service.plan_detail(plan["id"], self.OWNER)["runs"][0]
            self.assertEqual(run["status"], "succeeded")
            self.assertEqual(run["interpretation"]["failure_reason"], "model_budget_exhausted")
            self.assertEqual(len(provider.requests), 2)
            sent = json.loads(provider.requests[0])["messages"][1]["content"]
            self.assertNotIn("synthetic-sentinel", sent)
            self.assertNotIn("spend_cents", sent)  # Aggregates and definitions only, no rows.


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store, self.service = workspace(self.root)
        self.environment = patch.dict(os.environ, {"PROOFDESK_ALLOWED_HOSTS": "127.0.0.1"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(create_app(experiments=self.service), base_url="http://127.0.0.1")
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def post(self, path, payload, client=None, **headers):
        return (client or self.client).post(
            path, json=payload, headers={"X-ProofDesk-Request": "1", **headers}
        )

    def wait(self, job_id):
        for _ in range(200):
            job = self.client.get(f"/api/experiments/jobs/{job_id}").json()
            if job["status"] not in ("scheduled", "running"):
                return job
            time.sleep(0.05)
        self.fail("job did not finish")

    def test_session_scoping_journey_and_packet_download(self):
        self.assertEqual(self.client.get("/api/experiments").status_code, 401)
        datasets = self.client.get("/api/experiments/datasets").json()
        self.assertEqual(datasets[0]["id"], "synthetic-fixture")
        self.assertFalse(datasets[0]["raw_rows_served"])
        self.assertNotIn("local_path", datasets[0]["raw"])
        workspace_view = self.client.get("/api/workspace").json()
        self.assertEqual(workspace_view["experiments"]["generation_mode"], "deterministic")
        health = self.client.get("/api/health").json()
        self.assertEqual(health["scheduler"], "api_process_thread")
        plan = self.post("/api/experiments/plans", {**PLAN, "request_id": uuid.uuid4().hex}).json()
        self.assertEqual(plan["version"], 1)
        bad = self.post(
            "/api/experiments/plans",
            {
                **PLAN,
                "comparison": {"treatment": "x", "control": "no_email"},
                "request_id": uuid.uuid4().hex,
            },
        )
        self.assertEqual(bad.status_code, 409)
        self.assertEqual(bad.json()["detail"], "invalid_plan_comparison")
        job = self.post(
            f"/api/experiments/plans/{plan['id']}/runs", {"request_id": uuid.uuid4().hex}
        ).json()
        job = self.wait(job["id"])
        self.assertEqual(job["status"], "succeeded", job)
        detail = self.client.get(f"/api/experiments/plans/{plan['id']}").json()
        self.assertEqual(detail["runs"][0]["status"], "succeeded")
        self.assertEqual(detail["proposals"][0]["version"], 1)
        proposal = detail["proposals"][0]
        task = self.post(
            f"/api/experiments/plans/{plan['id']}/tasks",
            {
                "title": "Review",
                "assignee_label": "Sales manager",
                "proposed_action": "Review the packet",
                "due_date": "2026-11-12",
                "request_id": uuid.uuid4().hex,
            },
        ).json()
        approved = self.post(
            f"/api/experiments/tasks/{task['id']}/approve",
            {"proposal_sha256": proposal["sha256"], "request_id": uuid.uuid4().hex},
        ).json()
        self.assertEqual(approved["status"], "approved")
        scheduled = self.post(
            f"/api/experiments/tasks/{task['id']}/schedule",
            {"due_at": "now", "request_id": uuid.uuid4().hex},
        ).json()
        job = self.wait(scheduled["job_id"])
        self.assertEqual(job["status"], "succeeded", job)
        task = self.client.get(f"/api/experiments/plans/{plan['id']}").json()["tasks"][0]
        self.assertEqual(task["status"], "ready_for_review")
        download = self.client.get(
            f"/api/experiments/artifacts/{task['packet_artifact_id']}/packet.md"
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment", download.headers["content-disposition"])
        self.assertIn("# Experiment packet", download.text)
        with TestClient(create_app(experiments=self.service), base_url="http://127.0.0.1") as other:
            other.get("/api/workspace")
            self.assertEqual(other.get(f"/api/experiments/plans/{plan['id']}").status_code, 404)
            self.assertEqual(other.get(f"/api/experiments/jobs/{job['id']}").status_code, 404)
            self.assertEqual(
                other.get(
                    f"/api/experiments/artifacts/{task['packet_artifact_id']}/packet.md"
                ).status_code,
                404,
            )
            self.assertEqual(other.get("/api/experiments").json()["plans"], [])
            self.assertEqual(
                self.post(
                    f"/api/experiments/tasks/{task['id']}/cancel", {}, client=other
                ).status_code,
                404,
            )
        completed = self.post(
            f"/api/experiments/tasks/{task['id']}/complete",
            {"evidence_note": "Reviewed", "request_id": uuid.uuid4().hex},
        ).json()
        self.assertEqual(completed["status"], "completed")
        overview = self.client.get("/api/experiments").json()
        self.assertEqual(overview["tasks"][0]["status"], "completed")
        self.assertEqual(len(overview["jobs"]), 2)
        self.assertNotIn("lease_token", overview["jobs"][0])


@unittest.skipUnless(os.environ.get("PROOFDESK_DOCKER_TESTS") == "1", "explicit Docker opt-in")
class ExperimentDockerTests(unittest.TestCase):
    def test_real_sandbox_analysis_is_validated_and_reproducible(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            store = Store(root / "experiments")
            raw = synthetic_csv()
            (root / "fixture.csv").write_bytes(raw)
            manifests = [import_dataset(root / "fixture.csv", synthetic_source(raw), store.root)]
            if REAL_DATASET.is_file():
                manifests.append(import_dataset(REAL_DATASET, HILLSTROM, store.root))
            for manifest in manifests:
                store.save_dataset(manifest)
                executions = root / "executions"
                service = Experiments(
                    store,
                    execution_store=executions,
                    scheduler_interval=0.2,
                    launch=lambda job_id, token: run_job(
                        store, job_id, token, runner=docker_runner(), execution_store=executions
                    ),
                )
                owner = "docker-owner"
                plan = service.create_plan(
                    owner,
                    uuid.uuid4().hex,
                    {
                        **PLAN,
                        "dataset_id": manifest["id"],
                        "bootstrap": {"seed": 20080320, "resamples": 2000},
                    },
                )
                hashes = []
                for _ in range(2):
                    job = service.run_now(plan["id"], owner, uuid.uuid4().hex)
                    service.scheduler.tick()
                    job = service.job_detail(job["id"], owner)
                    self.assertEqual(job["status"], "succeeded", job)
                    run = service.plan_detail(plan["id"], owner)["runs"][0]
                    self.assertTrue(run["execution"]["cleanup"]["removed"])
                    self.assertEqual(
                        run["execution"]["validated_artifacts"][0]["validation"],
                        "analysis_result_contract_v1",
                    )
                    self.assertLess(run["execution"]["task_elapsed_seconds"], 30)
                    hashes.append(service.artifact_view(run["artifact_id"], owner)["sha256"])
                    VALIDATOR.validate(
                        json.loads((executions / run["execution_id"] / "record.json").read_text())
                    )
                self.assertEqual(len(set(hashes)), 1)
                if manifest["id"] == HILLSTROM.id:
                    run = service.plan_detail(plan["id"], owner)["runs"][0]
                    by_id = {m["id"]: m for m in run["metrics"]}
                    self.assertEqual(by_id["treatment.purchases"]["value"], 267)
                    self.assertEqual(by_id["control.purchases"]["value"], 122)
                    self.assertAlmostEqual(
                        by_id["conversion.difference_pp"]["value"], 267 / 21307 - 122 / 21306
                    )
                    self.assertTrue(
                        math.isfinite(by_id["spend.incremental_per_customer"]["interval"][0])
                    )
