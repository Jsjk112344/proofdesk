import copy
import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path

from backend.app.dealer.ingestion import sample_group
from backend.app.dealer.jobs import aggregate, run_job
from backend.app.dealer.matching import reconcile
from backend.app.dealer.store import DealerStore
from backend.app.execution.artifacts import Rejected
from backend.app.execution.controller import now


class DealerJobTests(unittest.TestCase):
    def test_fanout_leases_parent_waits_and_quota(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DealerStore(Path(tmp))
            store.save_group("a", sample_group())
            request = uuid.uuid4().hex
            parent = store.start_review("a", request)
            self.assertEqual(parent["id"], store.start_review("a", request)["id"])
            claimed = []
            for i in range(7):
                with store.transaction() as conn:
                    claimed.append(store.claim_due(conn, now(), str(i), 120, max_running=6))
            self.assertTrue(all(j and j["kind"] == "dealer_rooftop" for j in claimed[:6]))
            self.assertIsNone(claimed[-1])
            with store.transaction() as conn:
                self.assertRaises(Exception, store.verify_lease, conn, claimed[0]["id"], "wrong")
            with store.reading() as conn:
                self.assertEqual(len(store.jobs(conn, "a")), 25)
                self.assertEqual(store.jobs(conn, "b"), [])

    def test_rollup_preserves_metrics_and_surfaces_failed_analyst(self):
        metrics = {
            key: 0
            for key in (
                "open_leads",
                "cold_leads",
                "at_risk",
                "matched_leads",
                "matched_in_stock",
                "aged_60",
                "aged_90",
                "recoverable_gross",
                "floorplan_daily",
                "floorplan_to_date",
            )
        }
        metrics["at_risk"] = 5
        result = dict(
            rooftop_id="r02",
            metrics=metrics,
            queue=[],
            sources=[],
            brief=dict(status="failed", failure_reason="rooftop_brief_contract_rejected"),
        )
        value = aggregate([result], [])
        self.assertEqual(value["totals"]["at_risk"], 5)
        self.assertEqual(value["failures"][0]["rooftop_id"], "r02")

    @unittest.skipUnless(os.environ.get("PROOFDESK_DOCKER_TESTS") == "1", "opt-in Docker")
    def test_sandy_real_docker_reconciliation_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DealerStore(Path(tmp))
            group = sample_group()
            group["inventory"][137]["cost"] = 33900  # Include a genuine loss-making best match.
            store.save_group("a", group)
            parent = store.start_review("a", uuid.uuid4().hex)
            with store.transaction() as conn:
                # Atomic claims select all stores in order; exercise Sandy's actual lease.
                store.claim_due(conn, now(), "first", 120, max_running=6)
                job = store.claim_due(conn, now(), "sandy", 120, max_running=6)
            self.assertEqual(job["payload"]["rooftop_id"], "r02")
            result = run_job(store, job["id"], "sandy")
            self.assertEqual(result["status"], "succeeded", result["failure_reason"])
            expanded = store.result(result)
            counts = expanded["trace"]
            self.assertEqual(counts["open_leads"], expanded["metrics"]["open_leads"])
            self.assertEqual(counts["at_risk"], 40)
            self.assertEqual(counts["cold_leads"], 25)
            self.assertEqual(
                counts["scored_pairs"], 40 * (counts["cars_here"] + counts["cars_sister"])
            )
            self.assertEqual(
                next(e["counts"] for e in result["events"] if e["stage"] == "analysis_validated"),
                counts,
            )
            maria = next(lead for lead in expanded["queue"] if lead["customer"] == "Maria G.")
            self.assertEqual(maria["matches"][0]["stock_no"], "S00138")
            self.assertEqual(expanded["metrics"]["cold_leads"], 25)
            best = [lead["matches"][0] for lead in expanded["queue"] if lead["matches"]]
            self.assertTrue(any(unit["cost"] > unit["list_price"] for unit in best))
            self.assertEqual(
                expanded["metrics"]["recoverable_gross"],
                sum(unit["list_price"] - unit["cost"] for unit in best),
            )
            directory = store.root / "executions" / job["id"]
            records = [json.loads(p.read_text()) for p in directory.glob("*/record.json")]
            self.assertTrue(all(r["cleanup"]["removed"] for r in records))
            record = next(r for r in records if r["scenario"] == "dealer-rooftop")
            raw = (directory / record["id"] / "input.txt").read_bytes()
            value = json.loads((directory / record["id"] / "result.json").read_bytes())
            tampered = copy.deepcopy(value)
            tampered["k"]["cold_leads"] += 1
            self.assertRaises(Rejected, reconcile, tampered, json.loads(raw), raw)
            bad_score = copy.deepcopy(value)
            bad_score["r"][0][2][0][1][0] += 1
            self.assertRaises(Rejected, reconcile, bad_score, json.loads(raw), raw)
            self.assertEqual(parent["kind"], "dealer_rollup")
