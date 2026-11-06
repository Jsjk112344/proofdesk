"""Offline adversarial validation and opt-in real Docker lifecycle checks."""

import io
import json
import os
import signal
import subprocess
import sys
import tarfile
import time
import unittest
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker

from backend.app.execution.artifacts import Rejected, sha256, validate
from backend.app.execution.controller import (
    ROOT,
    STORE,
    docker_runner,
    execute,
    recover,
    serial_lock,
)
from backend.app.execution.runner import LABEL, Execution, Task
from backend.app.execution.scenarios import FAILURES, PROBES, scenario

SCHEMA = json.loads((ROOT / "docs/execution-record.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def archive(entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, content, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(content) if kind == tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = "/etc/passwd"
            tar.addfile(member, io.BytesIO(content))
    return buffer.getvalue()


class ArtifactTests(unittest.TestCase):
    def test_success_rejection_success_uses_only_own_evidence(self):
        class ReusedRunner:
            def execute(self, name, task, limits):
                self.evidence = {"task_name": name, "task_exit_code": 0}
                return Execution(
                    0, b"", archive([("out/result.json", b"{}", tarfile.REGTYPE)]), self.evidence
                )

            def cleanup(self, name):
                return {"removed": True, "reason": None}

        with TemporaryDirectory() as temp:
            runner = ReusedRunner()
            for oversized in (Task(b"x" * 32769, b""), Task(b"", b"x" * 32769)):
                first_path, first = execute(
                    runner, Task(b"pass", b"one"), {}, scenario="first", store=Path(temp)
                )
                path, rejected = execute(
                    runner, oversized, {}, scenario="rejected", store=Path(temp)
                )
                _, last = execute(
                    runner, Task(b"pass", b"three"), {}, scenario="last", store=Path(temp)
                )
                for record in (first, rejected, last):
                    VALIDATOR.validate(record)
                self.assertEqual(first["status"], "succeeded")
                self.assertEqual(last["status"], "succeeded")
                self.assertEqual(rejected["failure_reason"], "task_input_limit")
                self.assertEqual(rejected["evidence"], {})
                self.assertIsNone(rejected["exit_code"])
                self.assertFalse(rejected["dispatched"])
                self.assertEqual([p.name for p in path.parent.iterdir()], ["record.json"])
                self.assertLess(path.stat().st_size, 4096)
                self.assertEqual(first["evidence"]["task_name"], first["container_name"])
                self.assertEqual(last["evidence"]["task_name"], last["container_name"])
                self.assertEqual(json.loads(first_path.read_text()), first)
                self.assertNotEqual(first["id"], last["id"])

    def test_valid_and_wrong_content_with_successful_exit(self):
        data = archive([("out/result.json", b'{"value":1}', tarfile.REGTYPE)])
        self.assertEqual(validate(data, {"value": 1}), b'{"value":1}')
        with self.assertRaisesRegex(Rejected, "schema_or_content"):
            validate(data, {"value": 2})

    def test_unsafe_paths_and_types(self):
        for name in ("../result.json", "/out/result.json", "out/../result.json", "out/extra"):
            with self.subTest(name=name), self.assertRaises(Rejected):
                validate(archive([(name, b"{}", tarfile.REGTYPE)]), {})
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind), self.assertRaisesRegex(Rejected, "unsafe_artifact_type"):
                validate(archive([("out/result.json", b"", kind)]), {})

    def test_size_duplicates_malformed_and_missing(self):
        entries = [("out/result.json", b"{}", tarfile.REGTYPE)]
        for data in (
            archive([("out/result.json", b"x" * 16385, tarfile.REGTYPE)]),
            archive(entries * 2),
            archive([]),
            b"x" * 65537,
            b"invalid tar",
        ):
            with self.subTest(size=len(data)), self.assertRaises(Rejected):
                validate(data, {})

    def test_strict_json_types_and_duplicate_keys(self):
        for content in (b'{"v":true}', b'{"v":1.0}', b'{"v":1,"v":1}', b'{"v":NaN}'):
            with self.subTest(content=content), self.assertRaises(Rejected):
                validate(archive([("out/result.json", content, tarfile.REGTYPE)]), {"v": 1})

    def test_record_schema_and_fixture_contract(self):
        Draft202012Validator.check_schema(SCHEMA)
        task, expected = scenario("fixture")
        self.assertIn(b"SYNTHETIC", task.input)
        self.assertEqual(expected["total_cents"], 1600)

    def test_missing_docker_fails_with_record_and_no_host_execution(self):
        runner = docker_runner()
        runner.docker = str(ROOT / ".local/nonexistent-docker-executable")
        task, expected = scenario("fixture")
        with serial_lock():
            path, record = execute(runner, task, expected, scenario="missing-docker")
        VALIDATOR.validate(record)
        self.assertEqual(record["failure_reason"], "docker_unavailable")
        self.assertIsNone(record["exit_code"])
        self.assertFalse(record["cleanup"]["removed"])
        self.assertFalse((path.parent / "result.json").exists())


@unittest.skipUnless(os.environ.get("PROOFDESK_DOCKER_TESTS") == "1", "explicit Docker opt-in")
class DockerTests(unittest.TestCase):
    def test_success_rejection_success_same_docker_runner(self):
        with serial_lock():
            runner = docker_runner()
            task, expected = scenario("fixture")
            records = []
            for selected in (task, Task(task.script, b"x" * 32769), task):
                path, record = execute(runner, selected, expected, scenario="rejection-regression")
                VALIDATOR.validate(record)
                records.append(record)
                if not record["dispatched"]:
                    self.assertEqual({p.name for p in path.parent.iterdir()}, {"record.json"})
            self.assertEqual([r["status"] for r in records], ["succeeded", "failed", "succeeded"])
            self.assertEqual(records[1]["evidence"], {})
            self.assertIsNone(records[1]["exit_code"])
            self.assertEqual(len({r["id"] for r in records}), 3)
            self.assertEqual(records[0]["input_sha256"], sha256(task.input))
            self.assertEqual(records[2]["script_sha256"], sha256(task.script))
            for record in (records[0], records[2]):
                self.assertEqual(record["evidence"]["container_name"], record["container_name"])

    def test_fixture_and_all_probes(self):
        with (
            serial_lock(),
            patch.dict(os.environ, {"PROOFDESK_SYNTHETIC_SECRET": "not-a-real-credential"}),
        ):
            runner = docker_runner()
            canary = STORE / "test-host-canary.txt"
            canary.write_text("SYNTHETIC HOST CANARY\n")
            digest = sha256(canary.read_bytes())
            for name in ["fixture", *PROBES, "fixture"]:
                with self.subTest(name=name):
                    task, expected = scenario(name, canary)
                    path, record = execute(runner, task, expected, scenario=name)
                    VALIDATOR.validate(record)
                    self.assertEqual(record["failure_reason"], FAILURES.get(name))
                    self.assertEqual(
                        record["status"], "failed" if name in FAILURES else "succeeded"
                    )
                    self.assertTrue(record["cleanup"]["removed"])
                    self.assertEqual(sha256(canary.read_bytes()), digest)
                    self.assertEqual(
                        sha256((path.parent / "script.py").read_bytes()), record["script_sha256"]
                    )
                    if name == "incorrect":
                        self.assertEqual(record["exit_code"], 0)
                        self.assertFalse((path.parent / "result.json").exists())
                    if name == "timeout":
                        self.assertGreaterEqual(record["evidence"]["task_elapsed_seconds"], 4.9)
                        self.assertLess(record["evidence"]["task_elapsed_seconds"], 10)
                    if name == "fixture":
                        self.assertEqual(
                            json.loads((path.parent / "result.json").read_text()), expected
                        )
            self.assertEqual(
                runner.call("ps", "-aq", "--filter", f"label={LABEL}={runner.namespace}").strip(),
                b"",
            )

    def test_signals_and_crash_recovery(self):
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
            with self.subTest(signal=sig):
                self.check_signal(sig)

    def check_signal(self, sig):
        before = set(STORE.glob("*/record.json"))
        # Output belongs in .local; never print raw task output in test reports.
        log_path = STORE / ("signal-test-" + uuid.uuid4().hex + ".log")
        runner = docker_runner()
        with log_path.open("wb") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "backend.app.execution", "probe", "timeout"],
                cwd=ROOT,
                stdout=log,
                stderr=log,
            )
            record_path = None
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    paths = set(STORE.glob("*/record.json")) - before
                    if paths:
                        record_path = paths.pop()
                        record = json.loads(record_path.read_text())
                        # Wait for the actual fixture task, not just container creation.
                        code = subprocess.run(
                            [
                                runner.docker,
                                "top",
                                record["container_name"],
                                "-eww",
                                "-o",
                                "pid,args",
                            ],
                            capture_output=True,
                            timeout=3,
                        )
                        if b"<sandbox-task>" in code.stdout:
                            break
                    if process.poll() is not None:
                        self.fail("controller exited before signal injection")
                    time.sleep(0.05)
                else:
                    self.fail("fixture task did not start")
                process.send_signal(sig)
                process.wait(timeout=25)
                record = json.loads(record_path.read_text())
                if sig == signal.SIGKILL:
                    self.assertEqual(record["status"], "running")
                    with serial_lock():
                        task, expected = scenario("fixture")
                        _, refused = execute(runner, task, expected, scenario="before-recovery")
                        self.assertEqual(
                            refused["failure_reason"], "abandoned_containers_require_cleanup"
                        )
                        recover(runner)
                    record = json.loads(record_path.read_text())
                    self.assertEqual(record["failure_reason"], "controller_abandoned")
                else:
                    self.assertEqual(process.returncode, 130)
                    self.assertEqual(record["status"], "interrupted")
                VALIDATOR.validate(record)
                self.assertTrue(record["cleanup"]["removed"])
                with serial_lock():
                    task, expected = scenario("fixture")
                    _, subsequent = execute(runner, task, expected, scenario="after-interruption")
                self.assertEqual(subsequent["status"], "succeeded")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
                with serial_lock():
                    recover(runner)


if __name__ == "__main__":
    unittest.main()
