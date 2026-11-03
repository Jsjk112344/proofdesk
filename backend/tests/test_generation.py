"""No paid requests: fake wire protocol, workflow decisions, and opt-in Docker execution."""

import io
import json
import os
import tarfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from backend.app.execution.artifacts import sha256
from backend.app.execution.controller import ROOT, STORE, docker_runner, serial_lock
from backend.app.execution.runner import Execution, RunError
from backend.app.generation.provider import (
    Authorization,
    Budget,
    FakeProvider,
    ModelConfig,
    VultrProvider,
    WireResponse,
    _http_worker,
    fake_response,
    generate,
    vultr_transport,
)
from backend.app.generation.workflow import cases, recover_workflows, run_workflow
from backend.tests.test_execution import VALIDATOR

CONFIG = ModelConfig("offline-extraction-fixture")
GOOD = (ROOT / "fixtures/evaluation/offline-script.py").read_bytes()
BAD = b"from pathlib import Path\nPath('/work/out/result.json').write_text('{}')\n"


def sleeping_worker(pipe, key, payload, config):
    """Local transport-deadline fault injection, without opening any connection."""
    time.sleep(10)


def result_archive(value):
    buffer = io.BytesIO()
    raw = json.dumps(value).encode()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        member = tarfile.TarInfo("out/result.json")
        member.size = len(raw)
        tar.addfile(member, io.BytesIO(raw))
    return buffer.getvalue()


class RecordingRunner:
    """Returns labelled test outputs; never executes scripts on the host."""

    def __init__(self, outcomes=(), *, cleanup_ok=True, cleanup_raises=False):
        self.outcomes = iter(outcomes)
        self.cleanup_ok = cleanup_ok
        self.cleanup_raises = cleanup_raises
        self.tasks = []
        self.cleanups = []

    def check_ready(self):
        pass

    def execute(self, name, task, limits):
        self.tasks.append(task)
        self.evidence = {"task_name": name}
        outcome = next(self.outcomes, "success")
        if isinstance(outcome, Exception):
            raise outcome
        expected = next(
            json.loads(answer.read_text())
            for _, doc, answer, _ in cases()
            if doc.read_bytes() == task.input
        )
        code = 7 if outcome == "nonzero" else 0
        self.evidence["task_exit_code"] = code
        return Execution(
            code,
            b"SYNTHETIC runner output",
            result_archive({} if outcome == "incorrect" else expected),
            self.evidence,
        )

    def cleanup(self, name):
        self.cleanups.append(name)
        if self.cleanup_raises:
            raise RuntimeError("synthetic cleanup diagnostic")
        return {
            "removed": self.cleanup_ok,
            "reason": None if self.cleanup_ok else "injected_failure",
        }


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workflows = self.root / "workflows"
        self.executions = self.root / "executions"
        # Any accidental connection during an offline test fails immediately.
        self.network = patch("socket.create_connection", side_effect=AssertionError("offline only"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def run_loop(self, runner=None, responses=None, budget=None, provider=None):
        runner = runner or RecordingRunner()
        provider = provider or FakeProvider(
            responses if responses is not None else [fake_response(GOOD)]
        )
        path, record = run_workflow(
            runner,
            provider,
            CONFIG,
            budget or Budget(),
            store=self.workflows,
            execution_store=self.executions,
        )
        for execution in self.executions.glob("*/record.json"):
            VALIDATOR.validate(json.loads(execution.read_text()))
        self.assertEqual(json.loads(path.read_text()), record)
        return runner, provider, path, record

    def test_success_and_provenance(self):
        runner, provider, path, record = self.run_loop()
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(len(runner.tasks), 3)
        self.assertEqual(len(record["attempts"]), 1)
        self.assertEqual(record["budget"]["reserved_requests"], 1)
        self.assertEqual(record["budget"]["reserved_usd"], "0")
        self.assertTrue(record["attempts"][0]["executions"][-1]["held_out"])
        for execution in self.executions.glob("*/record.json"):
            run = json.loads(execution.read_text())
            self.assertEqual(run["source_kind"], "offline_provider_fixture")
            self.assertEqual(run["generation"]["workflow_id"], record["id"])
            generation = json.loads(
                (path.parent / run["generation"]["generation_record"]).read_text()
            )
            self.assertEqual(generation["response_sha256"], run["generation"]["response_sha256"])
            self.assertEqual(
                sha256((execution.parent / "script.py").read_bytes()), run["script_sha256"]
            )

    def test_incorrect_output_then_only_one_correction(self):
        runner, provider, path, record = self.run_loop(
            RecordingRunner(["incorrect"]), [fake_response(BAD), fake_response(GOOD)]
        )
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(len(record["attempts"]), 2)
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(len(runner.cleanups), 4)
        self.assertEqual(len(record["attempts"][0]["executions"]), 1)
        self.assertEqual(len(record["attempts"][1]["executions"]), 3)
        for number in (1, 2):
            receipt = json.loads((path.parent / f"attempt-{number}/generation.json").read_text())
            self.assertEqual(receipt["usage"]["total_tokens"], 600)
        self.assertEqual(record["budget"]["reserved_requests"], 2)
        prompts = b"\n".join(provider.requests).decode()
        self.assertNotIn("HOLDOUT-809", prompts)
        self.assertNotIn("CASE-17", prompts)
        self.assertNotIn("SYNTHETIC runner output", prompts)
        self.assertNotIn('"total_cents": 1600', prompts)
        for _, _, expected, _ in cases():
            self.assertNotIn(expected.read_text().strip(), prompts)

    def test_second_failure_stops_and_preserves_both_attempts(self):
        runner, provider, path, record = self.run_loop(
            RecordingRunner(["incorrect", "nonzero"]), [fake_response(BAD)] * 3
        )
        self.assertEqual(record["failure_reason"], "task_nonzero_exit")
        self.assertEqual(len(provider.requests), 2)
        self.assertEqual(len(runner.tasks), 2)
        self.assertEqual(len(list(path.parent.glob("attempt-*/generation.json"))), 2)
        runs = [json.loads(p.read_text()) for p in self.executions.glob("*/record.json")]
        self.assertEqual(
            {r["failure_reason"] for r in runs},
            {"artifact_schema_or_content_mismatch", "task_nonzero_exit"},
        )
        self.assertTrue(all((self.executions / r["id"] / "task.log").exists() for r in runs))

    def test_held_out_failure_does_not_disclose_document_or_answer(self):
        _, provider, _, record = self.run_loop(
            RecordingRunner(["success", "success", "incorrect"]),
            [fake_response(GOOD), fake_response(GOOD)],
        )
        self.assertEqual(record["status"], "succeeded")
        self.assertTrue(record["attempts"][0]["executions"][-1]["held_out"])
        prompt = b"\n".join(provider.requests).decode()
        self.assertNotIn("HOLDOUT-809", prompt)
        self.assertNotIn("Example Café Workshop", prompt)
        self.assertNotIn("2195", prompt)

    def test_execution_error_can_be_corrected(self):
        _, provider, _, record = self.run_loop(
            RecordingRunner(["nonzero"]), [fake_response(BAD), fake_response(GOOD)]
        )
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(len(provider.requests), 2)

    def test_policy_and_containment_failures_are_terminal(self):
        for reason in (
            "container_policy_mismatch",
            "kernel_limit_or_environment_mismatch",
            "unsafe_artifact_type",
            "unexpected_artifact_path",
            "output_limit",
            "task_deadline_exceeded",
        ):
            with self.subTest(reason=reason):
                runner, provider, _, record = self.run_loop(RecordingRunner([RunError(reason)]))
                self.assertEqual(record["failure_reason"], reason)
                self.assertEqual(len(provider.requests), 1)
                self.assertEqual(len(runner.tasks), 1)

    def test_cleanup_failure_stops_before_correction_or_next_case(self):
        for raises in (False, True):
            with self.subTest(raises=raises):
                runner, provider, _, record = self.run_loop(
                    RecordingRunner(["incorrect"], cleanup_ok=False, cleanup_raises=raises)
                )
                self.assertEqual(record["failure_reason"], "cleanup_unverified")
                self.assertEqual(len(provider.requests), 1)
                self.assertEqual(len(runner.tasks), 1)

    def test_budget_exhaustion_prevents_second_request(self):
        _, provider, path, record = self.run_loop(
            RecordingRunner(["incorrect"]),
            [fake_response(BAD), fake_response(GOOD)],
            budget=Budget(max_requests=1),
        )
        self.assertEqual(record["failure_reason"], "model_budget_exhausted")
        self.assertEqual(len(provider.requests), 1)
        second = json.loads((path.parent / "attempt-2/generation.json").read_text())
        self.assertFalse(second["dispatched"])
        self.assertIsNone(second["reservation"])
        self.assertEqual(record["budget"]["reserved_requests"], 1)

    def test_provider_failure_stops_without_execution_or_retry(self):
        for failure in (
            WireResponse(429, b"private diagnostic"),
            RunError("provider_deadline_exceeded"),
            RunError("provider_transport_cleanup_failed"),
            RuntimeError("synthetic secret"),
        ):
            with self.subTest(failure=type(failure).__name__):
                runner, provider, path, record = self.run_loop(
                    responses=[failure, fake_response(GOOD)]
                )
                self.assertEqual(record["status"], "failed")
                self.assertEqual(len(provider.requests), 1)
                self.assertFalse(runner.tasks)
                self.assertEqual(record["budget"]["reserved_requests"], 1)
                self.assertNotIn("synthetic secret", path.read_text())
                self.assertNotIn("private diagnostic", path.read_text())

    def test_missing_credentials_and_authorization_never_send(self):
        for key, reason in (
            (None, "missing_vultr_credentials"),
            ("synthetic-test-credential", "live_spending_not_authorized"),
        ):
            transport = Mock(side_effect=AssertionError("must not send"))
            with patch.dict(os.environ, {}, clear=True):
                runner, _, _, record = self.run_loop(
                    provider=VultrProvider(key=key, transport=transport)
                )
            self.assertEqual(record["failure_reason"], reason)
            self.assertFalse(runner.tasks)
            self.assertEqual(record["budget"]["reserved_requests"], 0)
            transport.assert_not_called()

    def test_unready_docker_stops_before_inference(self):
        runner = RecordingRunner()
        runner.check_ready = Mock(side_effect=RunError("docker_unavailable"))
        _, provider, _, record = self.run_loop(runner)
        self.assertEqual(record["failure_reason"], "docker_unavailable")
        self.assertFalse(provider.requests)

    def test_interrupt_preserves_request_reservation(self):
        _, provider, path, record = self.run_loop(responses=[KeyboardInterrupt()])
        self.assertEqual(record["status"], "interrupted")
        self.assertEqual(len(provider.requests), 1)
        self.assertTrue(path.exists())

    def test_abandoned_workflow_requires_explicit_recovery(self):
        _, _, path, record = self.run_loop()
        record["status"] = "running"
        path.write_text(json.dumps(record))
        generation_path = path.parent / "attempt-1/generation.json"
        pending = json.loads(generation_path.read_text())
        pending["status"] = "pending"
        generation_path.write_text(json.dumps(pending))
        _, provider, _, refused = self.run_loop()
        self.assertEqual(refused["failure_reason"], "abandoned_workflows_require_cleanup")
        self.assertFalse(provider.requests)
        self.assertEqual(recover_workflows(self.workflows), [record["id"]])
        self.assertEqual(json.loads(path.read_text())["failure_reason"], "controller_abandoned")
        recovered_request = json.loads(generation_path.read_text())
        self.assertEqual(recovered_request["failure_reason"], "controller_abandoned")
        self.assertEqual(recovered_request["budget"]["reserved_requests"], 1)
        self.assertEqual(self.run_loop()[-1]["status"], "succeeded")


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def request(self, response, *, config=CONFIG, budget=None, messages=None):
        provider = FakeProvider([response])
        path = self.root / str(len(list(self.root.iterdir())))
        path.mkdir()
        try:
            generate(
                provider,
                config,
                budget or Budget(),
                messages or [{"role": "user", "content": "x"}],
                path / "generation.json",
            )
        except RunError:
            pass
        return provider, path, json.loads((path / "generation.json").read_text())

    def test_http_errors_and_redirects_never_retry(self):
        for status in (301, 307, 400, 401, 429, 500, 503):
            provider, path, record = self.request(WireResponse(status, b"do not persist error"))
            self.assertEqual(
                record["failure_reason"],
                "provider_redirect_rejected" if status < 400 else "provider_http_error",
            )
            self.assertEqual(len(provider.requests), 1)
            self.assertEqual(record["budget"]["reserved_requests"], 1)
            self.assertFalse((path / "script.py").exists())
            self.assertNotIn("do not persist error", (path / "generation.json").read_text())

    def test_malformed_and_oversized_responses_stop(self):
        mutations = []

        def changed(edit, reason="provider_malformed_response"):
            value = json.loads(fake_response(GOOD).body)
            edit(value)
            mutations.append((WireResponse(200, json.dumps(value).encode()), reason))

        changed(lambda d: d.pop("usage"))
        changed(lambda d: d.update(model="other-provider-model"))
        changed(lambda d: d["usage"].update(prompt_tokens=True))
        changed(lambda d: d["usage"].update(total_tokens=1), "provider_usage_limit")
        changed(
            lambda d: d["usage"].update(completion_tokens=99999, total_tokens=100099),
            "provider_usage_limit",
        )
        changed(
            lambda d: d["choices"][0].update(finish_reason="length"), "provider_incomplete_response"
        )
        changed(lambda d: d["choices"][0]["message"].update(tool_calls=[{}]))
        changed(lambda d: d["choices"][0]["message"].update(content="```python\npass\n```"))
        changed(lambda d: d["choices"][0]["message"].update(content=""))
        changed(
            lambda d: d["choices"][0]["message"].update(content="x" * 32769),
            "generated_script_limit",
        )
        changed(lambda d: d["choices"][0]["message"].update(content="\x00"))
        mutations += [
            (WireResponse(200, b"not json"), "provider_malformed_response"),
            (WireResponse(200, b"x" * 65537), "provider_response_limit"),
            (WireResponse(200, b'{"choices":[],"choices":[]}'), "provider_malformed_response"),
        ]
        for response, reason in mutations:
            with self.subTest(size=len(response.body)):
                provider, path, record = self.request(response)
                self.assertEqual(record["status"], "failed")
                self.assertEqual(record["failure_reason"], reason)
                self.assertFalse((path / "script.py").exists())
                self.assertEqual(len(provider.requests), 1)
                self.assertEqual(record["budget"]["reserved_requests"], 1)
                if reason == "provider_usage_limit":
                    self.assertIsNotNone(record["usage"])

    def test_usage_and_explicit_output_limit_are_recorded(self):
        provider, path, record = self.request(fake_response(GOOD))
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(
            record["usage"], {"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600}
        )
        payload = json.loads(provider.requests[0])
        self.assertEqual(payload["max_completion_tokens"], 2048)
        self.assertFalse(payload["stream"])
        self.assertEqual(record["reservation"]["input_tokens"], 12000)
        self.assertEqual(record["request_sha256"], sha256((path / "request.json").read_bytes()))
        self.assertEqual(record["response_sha256"], sha256((path / "response.json").read_bytes()))
        self.assertEqual(record["usage_kind"], "synthetic")

    def test_input_budget_checked_before_request_or_contents_saved(self):
        provider, path, record = self.request(
            fake_response(GOOD), messages=[{"role": "user", "content": "x" * 12000}]
        )
        self.assertEqual(record["failure_reason"], "model_input_token_limit")
        self.assertFalse(record["dispatched"])
        self.assertFalse(provider.requests)
        self.assertEqual({p.name for p in path.iterdir()}, {"generation.json"})

    def test_token_request_and_cost_budgets(self):
        for budget in (
            Budget(max_total_tokens=14047),
            Budget(ceiling_usd="0.001", input_usd_per_million="1", output_usd_per_million="1"),
        ):
            provider, _, record = self.request(fake_response(GOOD), budget=budget)
            self.assertEqual(record["failure_reason"], "model_budget_exhausted")
            self.assertFalse(provider.requests)
        budget = Budget(ceiling_usd="0.1", input_usd_per_million="1", output_usd_per_million="2")
        _, _, record = self.request(WireResponse(500, b""), budget=budget)
        self.assertEqual(record["budget"]["reserved_usd"], "0.016096")
        self.assertIsNone(record["usage"])

    def test_approval_ledger_survives_reload_and_failed_request(self):
        ledger = self.root / "budgets" / "approved.json"
        first = Budget(
            max_requests=1, ceiling_usd="0.1", input_usd_per_million="1", output_usd_per_million="2"
        )
        first.bind(ledger)
        _, _, failed = self.request(WireResponse(500, b""), budget=first)
        self.assertEqual(failed["budget"]["reserved_requests"], 1)
        reopened = Budget(
            max_requests=1, ceiling_usd="0.1", input_usd_per_million="1", output_usd_per_million="2"
        )
        reopened.bind(ledger)
        provider, _, stopped = self.request(fake_response(GOOD), budget=reopened)
        self.assertEqual(stopped["failure_reason"], "model_budget_exhausted")
        self.assertFalse(provider.requests)
        self.assertEqual(stopped["budget"]["reserved_usd"], "0.016096")
        ledger.write_text("{}")
        with self.assertRaisesRegex(RunError, "ledger_invalid"):
            reopened.bind(ledger)

    def test_model_and_budget_configuration_rejected(self):
        for config in (
            {"model": ""},
            {"model": "x", "deadline_seconds": 61},
            {"model": "x", "max_output_tokens": True},
            {"model": "x", "max_response_bytes": 999999999},
        ):
            with self.subTest(config=config), self.assertRaises(RunError):
                ModelConfig(**config)
        for budget in (
            {"max_requests": 3},
            {"ceiling_usd": "NaN"},
            {"input_usd_per_million": "-1"},
        ):
            with self.subTest(budget=budget), self.assertRaises(RunError):
                Budget(**budget)

    def test_authorization_is_exact_and_endpoint_cannot_change(self):
        raw = {
            "config": asdict(CONFIG),
            "budget": {
                "max_requests": 2,
                "max_total_tokens": 28096,
                "ceiling_usd": "0.10",
                "input_usd_per_million": "1",
                "output_usd_per_million": "2",
            },
            "approval_reference": "SYNTHETIC TEST ONLY",
            "pricing_source": "https://www.vultr.com/test-synthetic-pricing",
            "pricing_checked_at": "2026-11-03",
        }
        path = self.root / "auth.json"
        path.write_text(json.dumps(raw))
        auth = Authorization.load(path)
        provider = VultrProvider(auth, key="synthetic-test-credential", transport=Mock())
        with patch.dict(os.environ, {}, clear=True):
            provider.ready(CONFIG, auth.budget)
            with self.assertRaisesRegex(RunError, "not_authorized"):
                provider.ready(CONFIG, Budget())
        with patch.dict(os.environ, {"VULTR_INFERENCE_BASE_URL": "https://example.invalid/v1"}):
            with self.assertRaisesRegex(RunError, "override_rejected"):
                provider.ready(CONFIG, auth.budget)
        raw["model_can_raise_budget"] = True
        path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(RunError, "invalid_live_authorization"):
            Authorization.load(path)

    def test_total_transport_deadline_without_network(self):
        started = time.monotonic()
        with self.assertRaisesRegex(RunError, "provider_deadline_exceeded"):
            vultr_transport(
                "synthetic-test-credential",
                b"{}",
                ModelConfig("test", deadline_seconds=1),
                worker=sleeping_worker,
            )
        self.assertLess(time.monotonic() - started, 4)

    def test_http_wire_headers_caps_and_no_redirect_following(self):
        for status, headers, reason in (
            (302, {}, None),
            (200, {"Content-Length": "65537"}, "provider_response_limit"),
            (200, {"Content-Encoding": "gzip"}, "provider_encoding_rejected"),
            (200, {}, None),
        ):
            response = Mock(status=status)
            response.getheader.side_effect = lambda name, default=None: headers.get(name, default)
            response.read.return_value = fake_response(GOOD).body
            connection = Mock()
            connection.getresponse.return_value = response
            pipe = Mock()
            with patch("http.client.HTTPSConnection", return_value=connection) as constructor:
                _http_worker(pipe, "synthetic-test-credential", b"{}", CONFIG)
            constructor.assert_called_once_with("api.vultrinference.com", timeout=30)
            self.assertEqual(connection.request.call_count, 1)
            self.assertEqual(
                connection.request.call_args.args[:2], ("POST", "/v1/chat/completions")
            )
            if reason:
                self.assertEqual(pipe.send.call_args.args[0][1], reason)
                response.read.assert_not_called()
            elif status != 200:
                self.assertEqual(pipe.send.call_args.args[0], ("http", 302, b""))
                response.read.assert_not_called()
            else:
                response.read.assert_called_once_with(65537)
            connection.close.assert_called_once()


@unittest.skipUnless(os.environ.get("PROOFDESK_DOCKER_TESTS") == "1", "explicit Docker opt-in")
class GeneratedDockerTests(unittest.TestCase):
    def test_offline_scripts_execute_correction_and_second_failure_stop(self):
        # Actual Docker, fake inference only. No paid provider or API key used.
        for name, scripts, status, attempts in (
            ("success", [GOOD], "succeeded", 1),
            ("correct-once", [BAD, GOOD], "succeeded", 2),
            ("fail-twice", [BAD, BAD, GOOD], "failed", 2),
        ):
            with self.subTest(name=name), serial_lock():
                provider = FakeProvider([fake_response(s) for s in scripts])
                path, record = run_workflow(docker_runner(), provider, CONFIG, Budget())
                self.assertEqual(record["status"], status)
                self.assertEqual(len(provider.requests), attempts)
                self.assertEqual(len(record["attempts"]), attempts)
                for attempt in record["attempts"]:
                    for execution in attempt["executions"]:
                        run_path = STORE / execution["id"] / "record.json"
                        run = json.loads(run_path.read_text())
                        VALIDATOR.validate(run)
                        self.assertTrue(run["cleanup"]["removed"])
                        self.assertEqual(run["source_kind"], "offline_provider_fixture")
                        self.assertEqual(run["generation"]["workflow_id"], record["id"])
                        self.assertEqual(
                            sha256((run_path.parent / "script.py").read_bytes()),
                            run["script_sha256"],
                        )
                self.assertEqual(json.loads(path.read_text()), record)
