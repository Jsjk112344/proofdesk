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
