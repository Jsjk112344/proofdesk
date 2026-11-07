import re
import unittest
from datetime import datetime

from scripts.generate_dealer_group import REFERENCE, RISK_COUNTS, generate


class DealerFixtures(unittest.TestCase):
    def test_seed_patterns_and_hero(self):
        roofs, units, leads = generate()
        self.assertEqual((len(roofs), len(units), len(leads)), (24, 3000, 11400))
        self.assertEqual(len({u["vin"] for u in units}), 3000)
        self.assertTrue(all(re.fullmatch("[A-HJ-NPR-Z0-9]{17}", u["vin"]) for u in units))
        active = [lead for lead in leads if lead["status"] not in ("sold", "lost")]
        self.assertEqual(len(active), 9000)
        self.assertEqual(
            sum(
                (REFERENCE - datetime.fromisoformat(lead["last_contact_at"])).total_seconds()
                >= 72 * 3600
                for lead in active
            ),
            25 + sum(round(n * 0.62) for i, n in enumerate(RISK_COUNTS) if i != 1),
        )
        maria = next(lead for lead in leads if lead["customer"] == "Maria G.")
        self.assertEqual(maria["rooftop_id"], "r02")
        self.assertEqual(
            next(u for u in units if u["stock_no"] == maria["vehicle_of_interest"])["status"],
            "sold",
        )
        self.assertEqual(next(u for u in units if u["stock_no"] == "S00138")["days_on_lot"], 74)

    def test_store_variation_is_in_source_records_and_sandy_stays_unchanged(self):
        from collections import Counter

        _, units, leads = generate()
        sold = {u["stock_no"] for u in units if u["status"] == "sold"}
        counts = Counter()
        for lead in leads:
            if lead["status"] in ("sold", "lost"):
                continue
            cold = (
                REFERENCE - datetime.fromisoformat(lead["last_contact_at"])
            ).total_seconds() >= 72 * 3600
            overdue = (
                bool(lead["appointment_at"])
                and datetime.fromisoformat(lead["appointment_at"]) < REFERENCE
            )
            if cold or lead["vehicle_of_interest"] in sold or overdue:
                counts[lead["rooftop_id"]] += 1
        self.assertEqual([counts[f"r{i + 1:02d}"] for i in range(24)], RISK_COUNTS)
        self.assertEqual(counts["r02"], 40)

    def test_generator_reproduces_committed_data(self):
        import io
        import tempfile
        from contextlib import redirect_stdout
        from pathlib import Path
        from unittest.mock import patch

        from scripts import generate_dealer_group as generator

        original = generator.OUT
        with tempfile.TemporaryDirectory() as tmp, patch.object(generator, "OUT", Path(tmp)):
            with redirect_stdout(io.StringIO()):
                generator.main()
            for name in (
                "rooftops.csv",
                "inventory.csv",
                "leads.csv",
                "group.json",
                "previous-night.json",
            ):
                with self.subTest(file=name):
                    self.assertEqual((Path(tmp) / name).read_text(), (original / name).read_text())
