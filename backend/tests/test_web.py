"""Offline web authorization/queue checks and an opt-in actual Docker journey."""

import json
import os
import unittest
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from backend.app.execution.controller import atomic_json
from backend.app.execution.runner import RunError
from backend.app.main import create_app
from backend.app.web_jobs import Jobs, extractor
from backend.app.web_worker import work
from backend.tests.test_generation import RecordingRunner


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "web-runs"
        self.jobs = Jobs(self.store)
        self.jobs.launch = lambda run_id: self.jobs.children.update(
            {run_id: Mock(poll=lambda: None)}
        )
        self.environment = patch.dict(os.environ, {"PROOFDESK_ALLOWED_HOSTS": "127.0.0.1"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(create_app(self.jobs), base_url="http://127.0.0.1")
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def start(self, document="development", request_id=None, **kwargs):
        return self.client.post(
            "/api/runs",
            json={
                "document_id": document,
                "request_id": request_id or uuid.uuid4().hex,
            },
            headers={"X-ProofDesk-Request": "1", **kwargs},
        )

    def test_sessions_origins_body_bounds_and_fixed_documents(self):
        self.assertEqual(self.start().status_code, 401)
        workspace = self.client.get("/api/workspace")
        self.assertEqual(workspace.status_code, 200)
        self.assertIn("HttpOnly", workspace.headers["set-cookie"])
        self.assertEqual(workspace.json()["generation_mode"], "deterministic")
        self.assertEqual(len(workspace.json()["documents"]), 3)
        self.assertEqual(self.start(Origin="https://untrusted.example").status_code, 403)
        self.assertEqual(self.start(document="../../private").status_code, 409)
        self.assertEqual(self.start(document={}).status_code, 409)
        response = self.client.post(
            "/api/runs",
            content="x" * 2049,
            headers={"X-ProofDesk-Request": "1", "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 413)
        self.assertFalse(self.jobs.records())

    def test_idempotency_concurrency_and_cross_session_reads(self):
        self.client.get("/api/workspace")
        key = uuid.uuid4().hex
        first = self.start(request_id=key).json()
        second = self.start(request_id=key).json()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.jobs.records()), 1)
        self.assertEqual(self.start().json()["detail"], "another_run_is_active")
        self.assertEqual(
            self.start(document="reordered", request_id=key).json()["detail"],
            "idempotency_conflict",
        )
        with TestClient(create_app(self.jobs), base_url="http://127.0.0.1") as other:
            other.get("/api/workspace")
            self.assertEqual(other.get("/api/runs/" + first["id"]).status_code, 404)
            self.assertEqual(other.get("/api/runs").json(), [])

    def test_worker_records_actual_validation_and_rejects_changed_artifact(self):
        record = self.jobs.start("development", "synthetic-owner", uuid.uuid4().hex)
        work(self.jobs, record["id"], RecordingRunner())
        saved = self.jobs.read(record["id"])
        view = self.jobs.public(saved, "synthetic-owner")
        self.assertEqual(saved["status"], "succeeded")
        self.assertEqual(view["result"]["total_cents"], 1600)
        self.assertEqual(view["extractor"]["source_kind"], "deterministic_synthetic_fixture")
        self.assertTrue(view["execution"]["cleanup"]["removed"])
        self.assertEqual(
            [e["stage"] for e in saved["events"]],
            ["queued", "preparing", "executing", "checking", "succeeded"],
        )
        artifact = self.store.parent / "executions" / saved["execution_id"] / "result.json"
        artifact.write_text("{}")
        with self.assertRaisesRegex(RunError, "saved_artifact_hash_mismatch"):
            self.jobs.public(saved, "synthetic-owner")

    def test_recovery_never_resends_and_quotas_persist(self):
        record = self.jobs.start("development", "synthetic-owner", uuid.uuid4().hex)
        restarted = Jobs(self.store, launch=Mock())
        restarted.reconcile()
        self.assertEqual(restarted.read(record["id"])["failure_reason"], "worker_abandoned")
        restarted.launch.assert_not_called()
        runner = RecordingRunner()
        work(self.jobs, record["id"], runner)
        self.assertFalse(runner.tasks)

        class InterruptedOwnership(RecordingRunner):
            def execute(inner, name, task, limits):
                restarted.reconcile()  # A new API process abandons the surviving worker.
                return super().execute(name, task, limits)

        pending = self.jobs.start("development", "synthetic-owner", uuid.uuid4().hex)
        work(self.jobs, pending["id"], InterruptedOwnership())
        saved = self.jobs.read(pending["id"])
        self.assertEqual(saved["failure_reason"], "worker_abandoned")
        self.assertIsNone(self.jobs.public(saved, "synthetic-owner")["result"])
        restarted.max_runs = 1
        with self.assertRaisesRegex(RunError, "web_run_quota_reached"):
            restarted.start("development", "new-owner", uuid.uuid4().hex)

    def test_bundle_tampering_and_worker_failure_are_terminal(self):
        record = self.jobs.start("development", "synthetic-owner", uuid.uuid4().hex)
        work(self.jobs, record["id"], RecordingRunner(cleanup_ok=False))
        self.assertEqual(self.jobs.read(record["id"])["failure_reason"], "cleanup_unverified")
        directory = Path(self.temp.name) / "bundle"
        directory.mkdir()
        atomic_json(
            directory / "manifest.json",
            {
                "source_kind": "vultr_model_generated",
                "script_sha256": "incorrect",
                "validated_cases": 3,
                "generation": {},
            },
        )
        (directory / "script.py").write_text("pass")
        with patch.dict(os.environ, {"PROOFDESK_EXTRACTOR_DIR": str(directory)}):
            with self.assertRaisesRegex(RunError, "extractor_bundle_invalid"):
                extractor()

    def test_worker_environment_excludes_model_credentials(self):
        with (
            patch.dict(os.environ, {"VULTR_INFERENCE_API_KEY": "synthetic-test-sentinel"}),
            patch("subprocess.Popen") as popen,
        ):
            self.jobs._launch(uuid.uuid4().hex)
        environment = popen.call_args.kwargs["env"]
        self.assertNotIn("VULTR_INFERENCE_API_KEY", environment)
        self.assertNotIn("synthetic-test-sentinel", json.dumps(environment))


@unittest.skipUnless(os.environ.get("PROOFDESK_DOCKER_TESTS") == "1", "explicit Docker opt-in")
class WebDockerTests(unittest.TestCase):
    def test_all_documents_through_real_web_worker(self):
        with TemporaryDirectory() as directory:
            jobs = Jobs(Path(directory) / "web-runs", launch=lambda _: None)
            for document in ("development", "reordered", "held-out"):
                record = jobs.start(document, "synthetic-docker-owner", uuid.uuid4().hex)
                work(jobs, record["id"])
                saved = jobs.read(record["id"])
                self.assertEqual(saved["status"], "succeeded", saved)
                result = jobs.public(saved, "synthetic-docker-owner")
                self.assertTrue(result["execution"]["cleanup"]["removed"])
                self.assertIsNotNone(result["result"])
