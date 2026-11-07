import tempfile
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path

from backend.app.dealer.handoff import approve, checked_rows, csv_export, edit, materialize, read
from backend.app.dealer.ingestion import sample_group
from backend.app.dealer.jobs import run_job
from backend.app.dealer.schedule import next_due, set_schedule
from backend.app.dealer.store import DealerStore
from backend.app.execution.controller import now
from backend.app.execution.runner import RunError


class DealerHandoff(unittest.TestCase):
    def test_approval_job_export_and_edit_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DealerStore(Path(tmp))
            group = sample_group()
            store.save_group("a", group)
            lead = dict(
                lead_id="L1",
                customer="Maria G.",
                first_name="Maria",
                salesperson="Avery Vale",
                trade_in="2017|Honda|CR-V|85000",
                wanted=dict(
                    year=2024, make="Toyota", model="RAV4 Hybrid", trim="XLE", color="blue"
                ),
                matches=[
                    dict(
                        stock_no="S00138",
                        year=2024,
                        make="Toyota",
                        model="RAV4 Hybrid",
                        trim="XLE",
                        color="silver",
                        list_price=32900,
                        days_on_lot=74,
                        store_name="Summit Sandy",
                        rooftop_id="r02",
                        transfer=False,
                    )
                ],
                risks=[],
            )
            result = dict(
                rooftop_id="r02",
                queue=[lead],
                metrics={},
                brief=dict(
                    status="succeeded", provenance="deterministic", rendered={"follow_ups": []}
                ),
            )
            materialize(store, "a", "source", result, group)
            with store.reading() as conn:
                fid = conn.execute("SELECT id FROM dealer_followups").fetchone()[0]
                row = read(store, conn, "a", fid)
                self.assertRaises(RunError, read, store, conn, "b", fid)
            versions = [{k: row[k] for k in ("id", "sha256", "version")}]
            job = approve(store, "a", "r02", versions, uuid.uuid4().hex)
            with store.transaction() as conn:
                store.claim_due(conn, now(), "lease", 120)
            done = run_job(store, job["id"], "lease")
            self.assertEqual(done["status"], "succeeded", done["failure_reason"])
            result = store.result(done)
            self.assertIn("Maria", result["files"]["follow-ups.md"])
            self.assertIn("L1,Avery Vale", result["files"]["crm-tasks.csv"])
            changed = edit(
                store,
                "a",
                fid,
                row["sha256"],
                dict(sms="Edited by manager", email_subject="Draft", email_body="Please review"),
            )
            self.assertIsNone(changed["approval"])
            with store.reading() as conn:
                self.assertRaises(RunError, checked_rows, store, conn, done)
            self.assertRaises(RunError, approve, store, "a", "r02", versions, uuid.uuid4().hex)
            self.assertIn("'=SUM", csv_export(["x"], [["=SUM(A1)"]]))

    def test_mountain_schedule_and_session_limit(self):
        self.assertEqual(
            next_due(datetime(2026, 11, 6, 7, tzinfo=UTC)), "2026-11-06T09:00:00+00:00"
        )
        self.assertEqual(
            next_due(datetime(2026, 11, 6, 10, tzinfo=UTC)), "2026-11-07T09:00:00+00:00"
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = DealerStore(Path(tmp))
            store.save_group("a", sample_group())
            self.assertTrue(set_schedule(store, "a", True)["enabled"])
            self.assertRaises(RunError, set_schedule, store, "b", True)
            self.assertFalse(set_schedule(store, "a", False)["enabled"])

    def test_reexport_keeps_other_approved_tasks_and_changed_data_refuses_approval(self):
        import copy

        from backend.app.dealer.contracts import rendered
        from backend.app.dealer.reasoning import deterministic
        from backend.tests.test_dealer_contracts import DealerContracts

        DealerContracts.setUpClass()
        group = DealerContracts.group
        first = copy.deepcopy(DealerContracts.lead)
        first.update(customer="Maria G.", salesperson="Avery Vale")
        first["matches"][0]["transfer"] = False
        second = copy.deepcopy(first)
        second.update(lead_id="L2", customer="Alex R.", first_name="Alex")
        result = dict(rooftop_id="r02", metrics={}, queue=[first, second])
        reading = deterministic("rooftop_brief", result, group)
        result["brief"] = dict(
            status="succeeded",
            provenance="deterministic",
            rendered=rendered(reading, result, group),
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = DealerStore(Path(tmp))
            store.save_group("a", group)
            materialize(store, "a", "source", result, group)
            with store.reading() as conn:
                rows = [
                    dict(row)
                    for row in conn.execute("SELECT * FROM dealer_followups ORDER BY rowid")
                ]

            def version(row):
                return [{k: row[k] for k in ("id", "version", "sha256")}]

            approve(store, "a", "r02", version(rows[0]), uuid.uuid4().hex)
            bundle = approve(store, "a", "r02", version(rows[1]), uuid.uuid4().hex)
            self.assertEqual(len(bundle["payload"]["versions"]), 2)
            # Complete the queued preparations, then replace source data assumptions.
            while True:
                with store.transaction() as conn:
                    job = store.claim_due(conn, now(), "lease", 120)
                if job is None:
                    break
                self.assertEqual(run_job(store, job["id"], "lease")["status"], "succeeded")
            changed = copy.deepcopy(group)
            changed["floorplan_daily_rate"] = 12
            store.save_group("a", changed)
            self.assertRaises(
                RunError, approve, store, "a", "r02", version(rows[0]), uuid.uuid4().hex
            )
