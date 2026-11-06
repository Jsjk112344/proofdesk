import re
import unittest
from datetime import datetime

from scripts.generate_dealer_group import REFERENCE, generate


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
            600,
        )
        maria = next(lead for lead in leads if lead["customer"] == "Maria G.")
        self.assertEqual(maria["rooftop_id"], "r02")
        self.assertEqual(
            next(u for u in units if u["stock_no"] == maria["vehicle_of_interest"])["status"],
            "sold",
        )
        self.assertEqual(next(u for u in units if u["stock_no"] == "S00138")["days_on_lot"], 74)
