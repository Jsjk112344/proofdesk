"""Prospect records: ownership, idempotency, quotas, draft versions and review state.

Smallest coherent record: offering, prospect URL or labelled sample, owner, sources,
claims, hypothesis, demonstration decision/result, draft version and review state, plus
saved progress and failure reasons. Records live under ignored .local/prospects/.
"""

import fcntl
import os
import re
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

from ..execution.artifacts import sha256, strict_json
from ..execution.controller import ROOT, atomic_json, now
from ..execution.runner import RunError
from ..web_jobs import bounded_file
from .drafting import draft_hash
from .evidence import SUPPORTED_CAPABILITY
from .retrieval import fixture_names, validate_url

ACTIVE = {"queued", "researching", "deciding", "demonstrating", "drafting"}
STAGES = ["queued", "researching", "deciding", "demonstrating", "drafting", "ready"]
MODES = {"deterministic", "live_model", "saved_replay"}
MAX_OFFERING = 1500
MIN_OFFERING = 20
MAX_SUBJECT = 160
MAX_BODY = 6000
MAX_HISTORY = 20
SESSION_QUOTA = 5
PUBLIC_SESSION_QUOTA = 3
SAMPLES = {
    "harbor-vale-freight": {
        "title": "Synthetic 3PL with manual paperwork",
        "note": (
            "Pages describe manual delivery-note and invoice handling; "
            "the demonstration is relevant."
        ),
    },
    "marigold-lane-bakery": {
        "title": "Synthetic bakery",
        "note": "Enough text to research, no document-handling work; the demonstration is skipped.",
    },
    "sparse-holding-page": {
        "title": "Synthetic placeholder page",
        "note": "Too little text to judge; the brief reports insufficient evidence.",
    },
}
DEFAULT_OFFERING = (
    "We build document-workflow automation for operations and finance teams: structured "
    "extraction from invoices, delivery notes and order forms into your existing systems, "
    "with every extracted value checkable against the source document. We start with a "
    "small pilot on your own sample documents."
)


def samples():
    available = set(fixture_names())
    return [
        {"id": name, **meta, "synthetic": True}
        for name, meta in SAMPLES.items()
        if name in available
    ]


class Prospects:
    def __init__(self, store=None, *, launch=None, live_plan=None, public_demo=None):
        self.store = Path(
            store or os.environ.get("PROOFDESK_PROSPECT_STORE", ROOT / ".local/prospects")
        )
        self.store.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.children = {}
        self.launch = launch or self._launch
        self.live_plan = (
            live_plan if live_plan is not None else os.environ.get("PROOFDESK_SALES_LIVE_PLAN")
        )
        # Public demo mode: synthetic scenarios only (unless a host is explicitly
        # allowlisted), smaller per-session quota, larger bounded total, no live model
        # unless separately enabled. The mode is reported truthfully by the API.
        self.public_demo = (
            public_demo
            if public_demo is not None
            else os.environ.get("PROOFDESK_PUBLIC_DEMO", "0") == "1"
        )
        default_total = "100" if self.public_demo else "20"
        self.max_total = min(
            200, max(1, int(os.environ.get("PROOFDESK_WEB_MAX_PROSPECTS", default_total)))
        )
        self.max_per_session = PUBLIC_SESSION_QUOTA if self.public_demo else SESSION_QUOTA
        self.url_allowlist = {
            host.strip().lower()
            for host in os.environ.get("PROOFDESK_PUBLIC_URL_ALLOWLIST", "").split(",")
            if host.strip()
        }

    @contextmanager
    def lock(self):
        with (self.store / ".lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def directory(self, prospect_id):
        if not isinstance(prospect_id, str) or not re.fullmatch(r"[a-f0-9]{32}", prospect_id):
            raise RunError("prospect_not_found")
        return self.store / prospect_id

    def path(self, prospect_id):
        return self.directory(prospect_id) / "record.json"

    def read(self, prospect_id):
        path = self.path(prospect_id)
        if not path.exists():
            raise RunError("prospect_not_found")
        return strict_json(bounded_file(path, 262144))

    def records(self):
        return [
            strict_json(bounded_file(p, 262144)) for p in sorted(self.store.glob("*/record.json"))
        ]

    def mode(self):
        """Live only with an operator plan and key in the API environment; never implicit.

        A public deployment additionally needs PROOFDESK_PUBLIC_LIVE=1, so a credential
        present for private use can never become a public paid endpoint by accident.
        """
        if self.live_plan and os.environ.get("VULTR_INFERENCE_API_KEY"):
            if self.public_demo and os.environ.get("PROOFDESK_PUBLIC_LIVE") != "1":
                return "deterministic"
            return "live_model"
        return "deterministic"

    def reconcile(self):
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

    def _launch(self, prospect_id):
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
            "PROOFDESK_SALES_LIVE_PLAN",
        }
        if self.live_plan:
            # The worker is the trusted controller for model calls; task sandboxes
            # still never receive this variable (the Docker runner uses env -i).
            allowed.add("VULTR_INFERENCE_API_KEY")
        environment = {k: v for k, v in os.environ.items() if k in allowed}
        environment["PROOFDESK_PROSPECT_STORE"] = str(self.store.resolve())
        self.children[prospect_id] = subprocess.Popen(
            [sys.executable, "-m", "backend.app.sales_worker", prospect_id],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def start(self, owner, request_id, *, offering, url=None, sample=None, mode=None):
        if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise RunError("invalid_request_id")
        if (
            not isinstance(offering, str)
            or not MIN_OFFERING <= len(offering.strip()) <= MAX_OFFERING
        ):
            raise RunError("offering_length_rejected")
        if (url is None) == (sample is None):
            raise RunError("prospect_target_required")
        if sample is not None:
            if sample not in {s["id"] for s in samples()}:
                raise RunError("unknown_sample_scenario")
            prospect = {
                "kind": "synthetic_fixture",
                "input_url": None,
                "sample": sample,
                "display_name": SAMPLES[sample]["title"],
            }
        else:
            normalized = validate_url(url)  # Syntax/host policy now; addresses in the worker.
            host = normalized.split("/")[2].lower()
            if self.public_demo and host not in self.url_allowlist:
                raise RunError("public_demo_samples_only")
            prospect = {
                "kind": "public_http",
                "input_url": normalized,
                "sample": None,
                "display_name": re.sub(r"^www\.", "", normalized.split("/")[2]),
            }
        mode = mode or self.mode()
        if mode not in MODES:
            raise RunError("invalid_generation_mode")
        with self.lock():
            records = self.records()
            for prior in records:
                if prior["owner"] == owner and prior["request_id"] == request_id:
                    if (
                        prior["prospect"] != prospect
                        or prior["offering"]["text"] != offering.strip()
                    ):
                        raise RunError("idempotency_conflict")
                    return prior
            if any(r["status"] in ACTIVE for r in records):
                raise RunError("another_prospect_is_active")
            if (
                len(records) >= self.max_total
                or sum(r["owner"] == owner for r in records) >= self.max_per_session
            ):
                raise RunError("prospect_quota_reached")
            prospect_id = uuid.uuid4().hex
            self.directory(prospect_id).mkdir(mode=0o700)
            record = {
                "schema_version": 1,
                "id": prospect_id,
                "owner": owner,
                "request_id": request_id,
                "created_at": now(),
                "finished_at": None,
                "status": "queued",
                "failure_reason": None,
                "failure_detail": None,
                "offering": {"text": offering.strip(), "capability": SUPPORTED_CAPABILITY},
                "prospect": prospect,
                "generation": {"mode": mode, "model": None, "receipts": {}, "diagnostics": []},
                "events": [{"stage": "queued", "at": now()}],
                "sources": [],
                "brief": None,
                "demo": None,
                "draft": None,
                "drafts_history": [],
                "review": {"state": "pending", "draft_sha256": None, "reviewed_at": None},
                "edit_request_ids": [],
            }
            atomic_json(self.path(prospect_id), record)
            try:
                self.launch(prospect_id)
            except Exception:
                record.update(
                    status="failed", failure_reason="worker_start_failed", finished_at=now()
                )
                atomic_json(self.path(prospect_id), record)
            return record

    def edit_draft(self, prospect_id, owner, request_id, *, subject, body, base_sha256):
        if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise RunError("invalid_request_id")
        if (
            not isinstance(subject, str)
            or not isinstance(body, str)
            or not 1 <= len(subject.strip()) <= MAX_SUBJECT
            or not 1 <= len(body.strip()) <= MAX_BODY
            or "\x00" in subject + body
        ):
            raise RunError("draft_length_rejected")
        with self.lock():
            record = self.read(prospect_id)
            if record["owner"] != owner:
                raise RunError("prospect_not_found")
            if request_id in record["edit_request_ids"]:
                return record
            if record["status"] != "ready" or not record["draft"]:
                raise RunError("draft_not_ready")
            if record["draft"]["sha256"] != base_sha256:
                raise RunError("draft_version_conflict")
            subject, body = subject.strip(), body.strip() + "\n"
            digest = draft_hash(subject, body)
            if digest == record["draft"]["sha256"]:
                record["edit_request_ids"].append(request_id)
                atomic_json(self.path(prospect_id), record)
                return record
            previous = record["draft"]
            record["drafts_history"] = ([previous] + record["drafts_history"])[:MAX_HISTORY]
            record["draft"] = {
                "version": previous["version"] + 1,
                "sha256": digest,
                "subject": subject,
                "body": body,
                "paragraphs": None,
                "citations": previous.get("citations"),
                "provenance": "human_edited",
                "derived_from": previous["sha256"],
                "created_at": now(),
            }
            # Editing changes the exact content, so any review no longer applies.
            record["review"] = {"state": "pending", "draft_sha256": None, "reviewed_at": None}
            record["edit_request_ids"] = (record["edit_request_ids"] + [request_id])[-50:]
            atomic_json(self.path(prospect_id), record)
            return record

    def review(self, prospect_id, owner, *, draft_sha256):
        with self.lock():
            record = self.read(prospect_id)
            if record["owner"] != owner:
                raise RunError("prospect_not_found")
            if record["status"] != "ready" or not record["draft"]:
                raise RunError("draft_not_ready")
            if record["draft"]["sha256"] != draft_sha256:
                raise RunError("draft_version_conflict")
            if record["review"]["state"] != "reviewed":
                record["review"] = {
                    "state": "reviewed",
                    "draft_sha256": draft_sha256,
                    "reviewed_at": now(),
                }
                atomic_json(self.path(prospect_id), record)
            return record

    def execution_view(self, execution_id):
        """Bounded, hash-checked view of a demonstration execution record."""
        if not re.fullmatch(r"[a-f0-9]{32}", execution_id or ""):
            raise RunError("execution_not_found")
        directory = self.store.parent / "executions" / execution_id
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
            "scenario",
            "input_sha256",
            "script_sha256",
        }
        view = {k: v for k, v in evidence.items() if k in keys}
        view["log"] = None
        view["result"] = None
        view["input"] = None
        if (directory / "task.log").is_file():
            view["log"] = bounded_file(directory / "task.log", 16384).decode(errors="replace")
        if (directory / "input.txt").is_file():
            view["input"] = bounded_file(directory / "input.txt", 32768).decode(errors="replace")
        if evidence["status"] == "succeeded" and evidence["cleanup"]["removed"]:
            data = bounded_file(directory / "result.json", 16384)
            if sha256(data) != evidence["validated_artifacts"][0]["sha256"]:
                raise RunError("saved_artifact_hash_mismatch")
            view["result"] = strict_json(data)
        return view

    def public(self, record, owner):
        if record["owner"] != owner:
            raise RunError("prospect_not_found")
        hidden = {"owner", "request_id", "edit_request_ids"}
        view = {k: v for k, v in record.items() if k not in hidden}
        view["execution"] = None
        if record.get("demo") and record["demo"].get("execution_id"):
            view["execution"] = self.execution_view(record["demo"]["execution_id"])
        return view

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
