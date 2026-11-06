"""Bounded synthetic queue. Model generation remains an operator CLI action."""

import fcntl
import os
import re
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from .execution.artifacts import sha256, strict_json
from .execution.controller import ROOT, atomic_json, now
from .execution.runner import RunError
from .generation.workflow import cases

ACTIVE = {"queued", "preparing", "executing", "checking"}
TITLES = ["Office supplies", "Reordered invoice", "Unicode & zero quantities"]


def bounded_file(path, limit=65536):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise RunError("evidence_file_rejected")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise RunError("evidence_file_rejected")
    return data


def documents():
    return [
        {"id": case, "title": title, "text": doc.read_text(), "synthetic": True}
        for (case, doc, _, _), title in zip(cases(), TITLES, strict=True)
    ]


def extractor():
    directory = os.environ.get("PROOFDESK_EXTRACTOR_DIR")
    if not directory:
        script = (ROOT / "fixtures/evaluation/offline-script.py").read_bytes()
        return script, {
            "source_kind": "deterministic_synthetic_fixture",
            "label": "Fixture extractor",
            "script_sha256": sha256(script),
            "model": None,
            "generation": None,
        }
    root = Path(directory)
    manifest = strict_json(bounded_file(root / "manifest.json"))
    script = bounded_file(root / "script.py", 32768)
    if (
        manifest.get("source_kind") != "vultr_model_generated"
        or manifest.get("script_sha256") != sha256(script)
        or manifest.get("validated_cases") != 3
        or not isinstance(manifest.get("generation"), dict)
    ):
        raise RunError("extractor_bundle_invalid")
    return script, manifest


class Jobs:
    def __init__(self, store=None, *, launch=None):
        self.store = Path(store or os.environ.get("PROOFDESK_WEB_STORE", ROOT / ".local/web-runs"))
        self.store.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.children = {}
        self.launch = launch or self._launch
        self.max_runs = min(100, max(1, int(os.environ.get("PROOFDESK_WEB_MAX_RUNS", "20"))))

    @contextmanager
    def lock(self):
        with (self.store / ".lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def path(self, run_id):
        if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise RunError("run_not_found")
        return self.store / run_id / "record.json"

    def read(self, run_id):
        path = self.path(run_id)
        if not path.exists():
            raise RunError("run_not_found")
        return strict_json(bounded_file(path))

    def records(self):
        return [strict_json(bounded_file(p)) for p in sorted(self.store.glob("*/record.json"))]

    def reconcile(self):
        # A restarted API never resends a request. CLI cleanup handles task leftovers.
        with self.lock():
            for record in self.records():
                child = self.children.get(record["id"])
                if record["status"] in ACTIVE and (child is None or child.poll() is not None):
                    record.update(
                        status="failed", failure_reason="worker_abandoned", finished_at=now()
                    )
                    record["events"].append({"stage": "failed", "at": now()})
                    atomic_json(self.path(record["id"]), record)
                if child is not None and child.poll() is not None:
                    self.children.pop(record["id"], None)

    def _launch(self, run_id):
        allowed = {
            "PATH",
            "HOME",
            "LANG",
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_CONFIG",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
            "PROOFDESK_EXTRACTOR_DIR",
        }
        environment = {k: v for k, v in os.environ.items() if k in allowed}
        environment["PROOFDESK_WEB_STORE"] = str(self.store.resolve())
        self.children[run_id] = subprocess.Popen(
            [sys.executable, "-m", "backend.app.web_worker", run_id],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def start(self, document_id, owner, request_id):
        if not isinstance(document_id, str) or document_id not in {d["id"] for d in documents()}:
            raise RunError("unknown_document")
        if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise RunError("invalid_request_id")
        with self.lock():
            records = self.records()
            for prior in records:
                if prior["owner"] == owner and prior["request_id"] == request_id:
                    if prior["document_id"] != document_id:
                        raise RunError("idempotency_conflict")
                    return prior
            if any(r["status"] in ACTIVE for r in records):
                raise RunError("another_run_is_active")
            if len(records) >= self.max_runs or sum(r["owner"] == owner for r in records) >= 5:
                raise RunError("web_run_quota_reached")
            _, source = extractor()
            run_id = uuid.uuid4().hex
            self.path(run_id).parent.mkdir(mode=0o700)
            record = {
                "schema_version": 1,
                "id": run_id,
                "owner": owner,
                "request_id": request_id,
                "document_id": document_id,
                "status": "queued",
                "failure_reason": None,
                "started_at": now(),
                "finished_at": None,
                "extractor": source,
                "execution_id": None,
                "events": [{"stage": "queued", "at": now()}],
            }
            atomic_json(self.path(run_id), record)
            try:
                self.launch(run_id)
            except Exception:
                record.update(
                    status="failed", failure_reason="worker_start_failed", finished_at=now()
                )
                atomic_json(self.path(run_id), record)
            return record

    def public(self, record, owner):
        if record["owner"] != owner:
            raise RunError("run_not_found")
        result = {k: v for k, v in record.items() if k not in {"owner", "request_id"}}
        result.update(result=None, execution=None, log=None)
        if record["execution_id"]:
            directory = self.store.parent / "executions" / record["execution_id"]
            evidence = strict_json(bounded_file(directory / "record.json"))
            keys = {
                "id",
                "status",
                "failure_reason",
                "exit_code",
                "source_kind",
                "execution_kind",
                "limits",
                "cleanup",
                "validated_artifacts",
                "image",
            }
            result["execution"] = {k: v for k, v in evidence.items() if k in keys}
            if (directory / "task.log").is_file():
                result["log"] = bounded_file(directory / "task.log", 16384).decode(errors="replace")
            if (
                record["status"] == "succeeded"
                and evidence["status"] == "succeeded"
                and evidence["cleanup"]["removed"]
            ):
                data = bounded_file(directory / "result.json", 16384)
                if sha256(data) != evidence["validated_artifacts"][0]["sha256"]:
                    raise RunError("saved_artifact_hash_mismatch")
                result["result"] = strict_json(data)
        return result

    def stop(self):
        for child in list(self.children.values()):
            if child.poll() is None:
                child.terminate()
        for child in list(self.children.values()):
            try:
                child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        self.reconcile()


def checkpoint():
    path = ROOT / ".local/inference-checkpoint.json"
    return strict_json(bounded_file(path)) if path.is_file() else None
