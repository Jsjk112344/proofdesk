import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.dealer.ingestion import SAMPLE
from backend.app.dealer.store import DealerStore
from backend.app.experiments.service import Experiments
from backend.app.experiments.store import Store
from backend.app.main import create_app
from backend.app.sales.prospects import Prospects
from backend.app.web_jobs import Jobs


class DealerApi(unittest.TestCase):
    def test_upload_protection_validation_templates_and_session_isolation(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict("os.environ", {"PROOFDESK_ALLOWED_HOSTS": "127.0.0.1"}),
        ):
            root = Path(tmp)
            dealer = DealerStore(root / "dealer")
            app = create_app(
                Jobs(root / "web", launch=lambda _: None),
                Prospects(root / "prospects", live_plan=""),
                Experiments(Store(root / "experiments"), launch=lambda *a: None, recover=None),
                dealer_store=dealer,
            )
            with TestClient(app, base_url="http://127.0.0.1") as client:
                self.assertEqual(client.get("/api/dealer").status_code, 401)
                client.get("/api/workspace")
                headers = {"X-ProofDesk-Request": "1", "Content-Type": "text/csv"}
                raw = (SAMPLE / "rooftops.csv").read_bytes()
                refused = client.post(
                    "/api/dealer/import/rooftops",
                    content=raw,
                    headers=dict(headers, Origin="https://foreign.example"),
                )
                self.assertEqual(refused.status_code, 403)
                for kind in ("rooftops", "leads", "inventory"):
                    response = client.post(
                        "/api/dealer/import/" + kind,
                        content=(SAMPLE / (kind + ".csv")).read_bytes(),
                        headers=headers,
                    )
                    self.assertEqual(response.status_code, 200, response.text[:200])
                    self.assertEqual(response.json()["rejected"], 0)
                    self.assertEqual(
                        client.get("/api/dealer/templates/" + kind + ".csv").status_code, 200
                    )
                result = client.post(
                    "/api/dealer/import", json={}, headers={"X-ProofDesk-Request": "1"}
                )
                self.assertEqual(result.status_code, 200, result.text[:200])
                self.assertEqual(client.get("/api/dealer/data").json()["counts"]["leads"], 11400)
                client.cookies.clear()
                client.get("/api/workspace")
                self.assertFalse(client.get("/api/dealer/data").json()["imported"])
                client.get("/api/dealer")
                changed = client.post(
                    "/api/dealer/assumptions",
                    json={"floorplan_daily_rate": 12, "match_distance_miles": 250},
                    headers={"X-ProofDesk-Request": "1"},
                )
                self.assertEqual(changed.status_code, 200)
                state = client.get("/api/dealer").json()
                self.assertFalse(state["saved_sample_review"])
                self.assertIsNone(state["rollup"]["totals"]["recoverable_gross"])
                self.assertEqual(
                    client.post(
                        "/api/dealer/import", json={}, headers={"X-ProofDesk-Request": "1"}
                    ).status_code,
                    409,
                )
