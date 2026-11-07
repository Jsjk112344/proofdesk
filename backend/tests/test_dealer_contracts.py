import copy
import json
import unittest

from backend.app.dealer.contracts import validate
from backend.app.dealer.ingestion import sample_group
from backend.app.dealer.reasoning import deterministic, messages
from backend.app.sales.contracts import ContractError


class DealerContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use only accepted sandbox outputs from the operator run if present.
        # Portable unit fixture below contains no execution/model claims.
        cls.group = sample_group()
        cls.lead = dict(
            lead_id="L1",
            first_name="Maria",
            trade_in="2017|Honda|CR-V|85000",
            wanted=dict(year=2024, make="Toyota", model="RAV4 Hybrid", trim="XLE", color="blue"),
            matches=[
                dict(
                    stock_no="S1",
                    year=2024,
                    make="Toyota",
                    model="RAV4 Hybrid",
                    trim="XLE",
                    color="silver",
                    list_price=32900,
                    days_on_lot=74,
                    store_name="Summit Sandy",
                    rooftop_id="r02",
                    status="in_stock",
                )
            ],
            risks=["Cold lead", "Vehicle sold"],
        )
        cls.result = dict(rooftop_id="r02", metrics=dict(cold_leads=25), queue=[cls.lead])

    def test_grounded_rendering_and_privacy(self):
        reading = deterministic("rooftop_brief", self.result, self.group)
        self.assertEqual(reading["follow_ups"][0]["lead_id"], "L1")
        wire = json.dumps(messages("rooftop_brief", self.result, self.group))
        self.assertNotIn("notes", wire)
        self.assertNotIn("last_contact_at", wire)
        self.assertNotIn("assigned_salesperson", wire)

    def test_group_match_finding_uses_dashboard_stock_denominator(self):
        result = dict(
            totals=dict(at_risk=85, matched_leads=80, matched_in_stock=71), rooftops=[], sources=[]
        )
        payload = json.loads(messages("group_brief", result, self.group)[1]["content"])
        self.assertIn(
            "[metric:matched_in_stock] at-risk leads have a best match in stock.",
            payload["safe_findings"],
        )
        reading = dict(
            headline="Review available stock.",
            findings=[payload["safe_findings"][1]],
            recommendations=[],
        )
        from backend.app.dealer.contracts import rendered

        self.assertEqual(
            rendered(
                validate(json.dumps(reading), "group_brief", result, self.group), result, self.group
            )["findings"],
            ["71 at-risk leads have a best match in stock."],
        )

    def test_rejects_untrusted_refs_quantities_features_and_sends(self):
        good = deterministic("rooftop_brief", self.result, self.group)
        for field, value in [
            ("lead_id", "L9"),
            ("stock_no", "S9"),
            ("reason", "Guaranteed ROI"),
            ("reason", "A $900 discount"),
            ("reason", "Review [metric:bogus]"),
            ("sms", "Hi [field:first_name], heated seats included. [Salesperson]"),
            ("sms", "Hi [field:first_name], send it now. [Salesperson]"),
        ]:
            bad = copy.deepcopy(good)
            bad["follow_ups"][0][field] = value
            with self.subTest(field=field, value=value):
                self.assertRaises(
                    ContractError,
                    validate,
                    json.dumps(bad),
                    "rooftop_brief",
                    self.result,
                    self.group,
                )
        self.assertRaises(
            ContractError,
            validate,
            json.dumps(
                dict(headline="Review [metric:store.fake]", findings=[], recommendations=[])
            ),
            "group_brief",
            dict(totals={}, rooftops=[], sources=[]),
            self.group,
        )
