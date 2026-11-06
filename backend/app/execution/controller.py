"""Controller-owned policy, validation, atomic records and serial recovery."""

import fcntl
import json
import os
import re
import signal
import subprocess
import threading
import uuid
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from .artifacts import Rejected, sha256, validate
from .runner import LABEL, DockerRunner, Limits, RunError, Runner, Task, limits_record

ROOT = Path(__file__).resolve().parents[3]
STORE = ROOT / ".local" / "executions"
TASK_BYTES = 32768
# Narrow extension for the fixed analysis program: a larger typed input (never a script)
# and a longer wall clock, still inside the same container policy and fsize ulimit.
ANALYSIS_INPUT_BYTES = 1024 * 1024
ANALYSIS_LIMITS = Limits(wall_seconds=30)
VALIDATIONS = {
    None: "exact_controller_schema_and_content",
    "analysis_result_contract_v1": "analysis_result_contract_v1",
    "dealer_result_contract_v1": "dealer_result_contract_v1",
}


def now():
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, value: dict):
    temp = path.with_suffix(".tmp")
    with temp.open("w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


@contextmanager
def serial_lock(store=STORE):
    store.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (store / ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RunError("another_controller_is_active") from exc
        yield


def docker_runner():
    return DockerRunner(
        (ROOT / "infra/task-image.txt").read_text().strip(),
        sha256(str(ROOT).encode())[:16],
    )


def _main_thread():
    # Signal handlers can only be installed from a process main thread; an in-process
    # test launch from another thread runs without them.
    return threading.current_thread() is threading.main_thread()


@contextmanager
def interruptions():
    def stop(signum, frame):
        raise KeyboardInterrupt

    if not _main_thread():
        yield
        return
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextmanager
def finish_without_interruption():
    if not _main_thread():
        yield
        return
    previous = {sig: signal.signal(sig, signal.SIG_IGN) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def revision():
    def git(*args):
        return (
            subprocess.check_output(["git", *args], cwd=ROOT, timeout=5, stderr=subprocess.DEVNULL)
            .decode()
            .strip()
        )

    try:
        return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}
    except (OSError, subprocess.SubprocessError):
        # A reviewed deployment tar has no .git; retain its recorded source baseline.
        try:
            data = json.loads((ROOT / "release.json").read_text())
            if re.fullmatch(r"[0-9a-f]{40}", data["commit"]) and type(data["dirty"]) is bool:
                return {"commit": data["commit"], "dirty": data["dirty"]}
        except (OSError, ValueError, TypeError, KeyError):
            pass
        return {"commit": None, "dirty": None}


def execute(
    runner: Runner,
    task: Task,
    expected: dict,
    *,
    scenario: str,
    store=STORE,
    limits=None,
    source_kind="deterministic_synthetic_fixture",
    generation=None,
    validator=None,
    validation=None,
    task_bytes=TASK_BYTES,
):
    """Run one task in a fresh sandbox and validate its single artifact.

    `validator` (with its `validation` label) replaces exact comparison with `expected`
    for contracts whose values are computed, not known beforehand. `task_bytes` bounds
    the input only; scripts are always limited to TASK_BYTES.
    """
    limits = limits or Limits()
    if validation not in VALIDATIONS or (validator is None) != (validation is None):
        raise RunError("invalid_validation_contract")
    if type(task_bytes) is not int or not TASK_BYTES <= task_bytes <= ANALYSIS_INPUT_BYTES:
        raise RunError("invalid_task_input_limit")
    run_id = uuid.uuid4().hex
    name = "proofdesk-" + run_id
    directory = store / run_id
    directory.mkdir(parents=True, mode=0o700)
    rejected = len(task.script) > TASK_BYTES or len(task.input) > task_bytes
    expected_bytes = json.dumps(expected, sort_keys=True).encode()
    record = {
        "schema_version": 2,
        "id": run_id,
        "container_name": name,
        "started_at": now(),
        "finished_at": None,
        "scenario": scenario,
        "source_kind": source_kind,
        "generation": generation,
        "execution_kind": "local_docker",
        "revision": revision(),
        "input_sha256": None if rejected else sha256(task.input),
        "script_sha256": None if rejected else sha256(task.script),
        "expected_sha256": None if rejected else sha256(expected_bytes),
        "dispatched": False,
        "input_rejection": (
            {"input_bytes": len(task.input), "script_bytes": len(task.script), "limit": task_bytes}
            if rejected
            else None
        ),
        "image": getattr(runner, "image", None),
        "limits": limits_record(limits),
        "status": "running",
        "failure_reason": None,
        "exit_code": None,
        "evidence": {},
        "validated_artifacts": [],
        "cleanup": {"removed": False, "reason": "not_attempted"},
    }
    # Reject before persisting contents (or hashing oversized data). Rejections
    # retain only bounded metadata; they never touch reusable runner state.
    if not rejected:
        (directory / "input.txt").write_bytes(task.input)
        (directory / "script.py").write_bytes(task.script)
        (directory / "expected.json").write_bytes(expected_bytes)
    record_path = directory / "record.json"
    atomic_json(record_path, record)
    try:
        if rejected:
            raise RunError("task_input_limit")
        record["dispatched"] = True
        atomic_json(record_path, record)
        result = runner.execute(name, task, limits)
        record["exit_code"] = result.exit_code
        record["evidence"] = result.evidence
        (directory / "task.log").write_bytes(result.logs)
        if result.exit_code:
            raise RunError("task_nonzero_exit")
        artifact = validate(result.archive, expected, validator)
        (directory / "result.json").write_bytes(artifact)
        record["validated_artifacts"] = [
            {
                "path": "result.json",
                "media_type": "application/json",
                "size_bytes": len(artifact),
                "sha256": sha256(artifact),
                "validation": VALIDATIONS[validation],
            }
        ]
        record["status"] = "succeeded"
    except (RunError, Rejected) as exc:
        record["status"] = "failed"
        record["failure_reason"] = str(exc)
    except KeyboardInterrupt:
        record["status"] = "interrupted"
        record["failure_reason"] = "controller_interrupted"
    except Exception:
        # Preserve a stable failure without accidentally persisting secrets in
        # exception messages. The local CLI is not a public execution interface.
        record["status"] = "failed"
        record["failure_reason"] = "controller_internal_error"
    finally:
        with finish_without_interruption():
            if record["dispatched"]:
                record["evidence"] = deepcopy(getattr(runner, "evidence", record["evidence"]))
                if record["exit_code"] is None:
                    record["exit_code"] = record["evidence"].get("task_exit_code")
                try:
                    record["cleanup"] = runner.cleanup(name)
                except Exception:
                    record["cleanup"] = {"removed": False, "reason": "cleanup_internal_error"}
            else:
                record["cleanup"] = {"removed": True, "reason": "not_started"}
            if not record["cleanup"]["removed"] and record["status"] == "succeeded":
                record["status"] = "failed"
                record["failure_reason"] = "cleanup_unverified"
            record["finished_at"] = now()
            atomic_json(record_path, record)
    return record_path, record


def recover(runner: DockerRunner, store=STORE):
    """Caller holds serial lock. Only this checkout's labelled containers qualify."""
    names = (
        runner.call(
            "ps", "-a", "--filter", f"label={LABEL}={runner.namespace}", "--format", "{{.Names}}"
        )
        .decode()
        .splitlines()
    )
    for name in names:
        if not re.fullmatch(r"proofdesk-[0-9a-f]{32}", name):
            raise RunError("unexpected_recovery_container_name")
        result = runner.cleanup(name)
        if not result["removed"]:
            raise RunError("recovery_cleanup_failed")
    # Reconcile records even if Docker already removed a container. No other
    # controller can be active in this checkout while the lock is held.
    recovered = []
    for path in sorted(store.glob("*/record.json")):
        record = json.loads(path.read_text())
        if record["status"] != "running" and record["cleanup"]["removed"]:
            continue
        record["cleanup"] = {"removed": True, "reason": "reconciled_by_recovery"}
        if record["status"] == "running":
            record["status"] = "failed"
            record["failure_reason"] = "controller_abandoned"
            record["finished_at"] = now()
        atomic_json(path, record)
        recovered.append(record["id"])
    return {"removed_containers": names, "reconciled_records": recovered}
