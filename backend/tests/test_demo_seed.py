"""Public initialization counts against quotas and never crosses session ownership."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.app.demo import seed_demo
from backend.app.execution.runner import RunError
from backend.app.sales.agent import run_prospect
from backend.app.sales.prospects import Prospects
from backend.tests.test_experiments import PLAN, workspace
from backend.tests.test_generation import RecordingRunner


class DemoSeedTests(unittest.TestCase):
    def test_seed_is_idempotent_isolated_and_does_not_reapprove_edits(self):
        with TemporaryDirectory() as temp, patch("backend.app.demo.BENCHMARK_PLAN", PLAN):
            root = Path(temp)
            store, service = workspace(root, public_demo=True)
            prospects = Prospects(root / "prospects", launch=lambda _: None, public_demo=True)
            initial = seed_demo(service, prospects, "visitor-a")
            self.assertFalse(initial["ready"])
            run_prospect(
                prospects,
                initial["prospect_id"],
                runner=RecordingRunner(),
                execution_store=root / "executions",
            )
            service.scheduler.tick()
            self.assertFalse(seed_demo(service, prospects, "visitor-a")["ready"])
            service.scheduler.tick()
            ready = seed_demo(service, prospects, "visitor-a")
            self.assertTrue(ready["ready"])
            overview = service.overview("visitor-a")
            self.assertEqual(
                (len(overview["plans"]), len(overview["jobs"]), len(overview["tasks"])), (1, 2, 1)
            )
            self.assertEqual(len(prospects.records()), 1)
            with self.assertRaises(RunError):
                service.plan_detail(initial["plan_id"], "visitor-b")
            detail = service.plan_detail(initial["plan_id"], "visitor-a")
            proposal = detail["proposals"][0]
            content = {**proposal["content"], "notes": "Visitor correction"}
            service.save_proposal(
                initial["plan_id"],
                "visitor-a",
                "a" * 32,
                content,
                base_version=proposal["version"],
            )
            self.assertTrue(seed_demo(service, prospects, "visitor-a")["ready"])
            self.assertEqual(
                service.plan_detail(initial["plan_id"], "visitor-a")["tasks"][0]["approval"][
                    "proposal_sha256"
                ],
                proposal["sha256"],
            )
            self.assertEqual(len(service.overview("visitor-a")["jobs"]), 2)
            second = seed_demo(service, prospects, "visitor-b")
            self.assertNotEqual(second["plan_id"], initial["plan_id"])
            self.assertNotEqual(second["prospect_id"], initial["prospect_id"])

    def test_private_runtime_cannot_seed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            _, service = workspace(root)
            prospects = Prospects(root / "prospects", launch=lambda _: None)
            with self.assertRaises(RunError):
                seed_demo(service, prospects, "visitor")
