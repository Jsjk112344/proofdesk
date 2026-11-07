import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from backend.app.dealer.ingestion import MAX_BYTES, parse_csv, sample_group, template
from backend.app.dealer.store import DealerStore
from backend.app.execution.runner import RunError


class IngestionTests(unittest.TestCase):
    def test_headers_limits_and_malformed(self):
        raw = (
            template("rooftops") + "s1,Demo,Test City,40,-111,Toyota,Alex Vale,Sam Vale\n"
        ).encode()
        rows, report = parse_csv("rooftops", raw.replace(b"lat,lng", b"Latitude,Longitude"))
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(rows[0]["lat"], 40)
        self.assertEqual(parse_csv("rooftops", raw + raw.split(b"\n")[1] + b"\n")[1]["rejected"], 1)
        self.assertRaises(RunError, parse_csv, "leads", b"x" * (MAX_BYTES + 1))
        self.assertRaises(RunError, parse_csv, "leads", b"lead_id,name\nx,Jane\n")
        bad = raw.replace(b"40,-111", b"nan,-111")
        self.assertEqual(parse_csv("rooftops", bad)[1]["rejected"], 1)
        self.assertRaises(
            RunError, parse_csv, "rooftops", raw.replace(b"name,", b"name,Store Name,")
        )

    def test_sample_and_isolation(self):
        data = sample_group()
        self.assertTrue(all(r["rejected"] == 0 for r in data["validation"]))
        self.assertEqual(len(data["leads"]), 11400)
        self.assertLess(
            datetime.fromisoformat(data["previous"]["reference_time"]),
            datetime.fromisoformat(data["reference_time"]),
        )
        with tempfile.TemporaryDirectory() as tmp:
            store = DealerStore(Path(tmp))
            store.save_group("owner-a", data)
            with store.reading() as conn:
                self.assertRaises(RunError, store.group, conn, "owner-b")
            self.assertRaises(RunError, store.finish_import, "owner-b")

    def test_never_contacted_lead_uses_creation_time(self):
        import csv
        import io

        from backend.app.dealer.ingestion import SAMPLE

        rows = list(csv.DictReader(io.StringIO((SAMPLE / "leads.csv").read_text())))
        lead = rows[0]
        lead["last_contact_at"] = ""
        lead["first_contact_at"] = ""
        lead["status"] = "new"
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(lead))
        writer.writeheader()
        writer.writerow(lead)
        values, report = parse_csv("leads", output.getvalue().encode())
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(values[0]["last_contact_at"], "")

    def test_review_clock_advances_uploaded_age_and_preserves_sample_story(self):
        from datetime import timedelta

        from backend.app.dealer.matching import review_snapshot

        group = sample_group()
        at = (datetime.fromisoformat(group["reference_time"]) + timedelta(days=2)).isoformat()
        shifted = review_snapshot(group, at)
        self.assertEqual(shifted["inventory"][137]["days_on_lot"], 74)
        maria = next(lead for lead in shifted["leads"] if lead["customer"] == "Maria G.")
        self.assertEqual(
            (datetime.fromisoformat(at) - datetime.fromisoformat(maria["created_at"])).days, 9
        )
        group["synthetic"] = False
        uploaded = review_snapshot(group, at)
        self.assertEqual(uploaded["inventory"][137]["days_on_lot"], 76)
        self.assertEqual(uploaded["leads"][475]["created_at"], group["leads"][475]["created_at"])
