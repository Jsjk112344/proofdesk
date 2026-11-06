"""Durable jobs: an in-process scheduler that claims due work and a worker that executes it.

The API process runs the scheduler thread (the browser is a client, never the scheduler).
Each due job is claimed under a lease inside one SQLite transaction, then executed by a
trusted subprocess that re-validates its lease before every write. A lost worker is
requeued once (both job kinds are deterministic and idempotent) or failed; duplicate
dispatch cannot create a second run, task result or final artifact because artifacts are
unique per job and every write is conditional on the lease.
"""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from ..execution.artifacts import Rejected, sha256, strict_json
from ..execution.controller import (
    ANALYSIS_INPUT_BYTES,
    ANALYSIS_LIMITS,
    ROOT,
    STORE,
    docker_runner,
    execute,
    interruptions,
    now,
    recover,
    serial_lock,
)
from ..execution.runner import RunError, Task
from .contracts import (
    derive_metrics,
    plan_hash,
    plan_line,
    proposal_hash,
    validate_proposal,
    validate_result,
)
from .packet import assemble_packet, render_markdown
from .reasoning import LIVE_PLAN_VARIABLE, interpret

LEASE_SECONDS = 120
PROGRAM_PATH = Path(__file__).with_name("analysis_program.py")
ANALYSIS_VALIDATION = "analysis_result_contract_v1"
EMPTY_ASSUMPTIONS = {"audience_size": None, "gross_margin": None, "campaign_cost_usd": None}
EMPTY_SAMPLE = {"minimum_detectable_pp": None, "alpha": None, "power": None}


def program_bytes():
    return PROGRAM_PATH.read_bytes()


def docker_recovery(execution_store):
    """Startup recovery for the sandbox store: labelled containers removed, records reconciled."""

    def run():
        with serial_lock(Path(execution_store)):
            return recover(docker_runner(), Path(execution_store))

    return run


def program_sha256():
    return sha256(program_bytes())


class Scheduler:
    """Claims due jobs and launches one worker subprocess per claim."""

    def __init__(self, store, *, launch=None, interval=2.0, recover=None):
        self.store = store
        self.launch = launch or self._launch
        self.interval = interval
        self.recover = recover  # Startup-only sandbox recovery; None skips it.
        self.children = {}
        self.last_error = None
        self.last_recovery = None
        self._stop = threading.Event()
        self._thread = None

    def reconcile(self, *, startup=False):
        """A restarted API owns no workers: running jobs without a live child are lost.

        At startup the existing execution recovery removes this checkout's labelled
        containers (a terminated worker may have been unable to) before any requeued job
        is dispatched again. Nothing is retried here; requeueing is bounded per job.
        """
        if startup and self.recover is not None:
            try:
                self.last_recovery = self.recover()
            except RunError as exc:
                self.last_recovery = {"error": exc.reason}
            except Exception as exc:  # Recovery must never prevent the API from starting.
                self.last_recovery = {"error": type(exc).__name__}
        with self.store.transaction() as conn:
            for job_id, (child, _) in list(self.children.items()):
                if child.poll() is not None:
                    self.children.pop(job_id, None)
            lost = []
            for row in conn.execute("SELECT * FROM jobs WHERE status = 'running'").fetchall():
                if row["id"] not in self.children:
                    lost.append(row["id"])
            if lost:
                changed = self.store.expire_leases(conn, now(), job_ids=lost)
                for job in changed:
                    if job["task_id"] and job["status"] == "failed":
                        task = self.store.task(conn, job["task_id"])
                        if task["status"] == "running":
                            self.store.set_task_status(conn, task, "failed")

    def tick(self):
        self.reconcile()
        token = uuid.uuid4().hex
        with self.store.transaction() as conn:
            job = self.store.claim_due(conn, now(), token, LEASE_SECONDS)
        if job is None:
            return None
        try:
            self.launch(job["id"], token)
        except Exception:
            with self.store.transaction() as conn:
                saved = self.store.job(conn, job["id"])
                self.store.set_job_status(
                    conn,
                    saved,
                    "failed",
                    failure_reason="worker_start_failed",
                    finished_at=now(),
                    lease_token=None,
                    lease_until=None,
                )
            return None
        return job

    def _launch(self, job_id, token):
        allowed = {
            "PATH",
            "HOME",
            "LANG",
            "PROOFDESK_PUBLIC_DEMO",
            "PROOFDESK_PUBLIC_LIVE",
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_CONFIG",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
            "PROOFDESK_EXPERIMENT_STORE",
            LIVE_PLAN_VARIABLE,
        }
        if os.environ.get(LIVE_PLAN_VARIABLE):
            allowed.add("VULTR_INFERENCE_API_KEY")  # Trusted worker; sandboxes never see it.
        environment = {k: v for k, v in os.environ.items() if k in allowed}
        environment["PROOFDESK_EXPERIMENT_STORE"] = str(self.store.root.resolve())
        child = subprocess.Popen(
            [sys.executable, "-m", "backend.app.experiments.worker", job_id, token],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.children[job_id] = (child, token)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.tick()
                self.last_error = None
            except Exception as exc:  # The scheduler must outlive one bad tick.
                self.last_error = type(exc).__name__
            self._stop.wait(self.interval)

    def start(self):
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._loop, name="experiment-scheduler", daemon=True
            )
            self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
        for child, _ in list(self.children.values()):
            if child.poll() is None:
                child.terminate()
        for child, _ in list(self.children.values()):
            try:
                child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        self.reconcile()


def analysis_task_input(dataset_input: bytes, spec) -> bytes:
    header, rows = dataset_input.split(b"\n", 1)
    return header + b"\n" + plan_line(spec).encode() + b"\n" + rows


def run_job(
    store,
    job_id,
    lease_token,
    *,
    runner=None,
    provider=None,
    authorization=None,
    execution_store=None,
    sandbox_wait=20,
    ledgers=None,
):
    """Execute one claimed job. Every write re-validates the lease; a lost lease stops."""
    execution_store = Path(execution_store or STORE)
    try:
        with store.transaction() as conn:
            job = store.job(conn, job_id)
            store.verify_lease(conn, job_id, lease_token)
            plan = store.plan(conn, job["plan_id"], job["owner"])
            store.heartbeat(conn, job, lease_token, LEASE_SECONDS, stage="started")
    except RunError as exc:
        if exc.reason != "job_lease_lost":
            raise
        with store.reading() as conn:  # A duplicate or late worker changes nothing.
            return store.job(conn, job_id)
    outcome = None
    try:
        with interruptions():
            if job["kind"] == "analyze_plan":
                outcome = _analyze(
                    store,
                    job,
                    plan,
                    lease_token,
                    runner=runner,
                    provider=provider,
                    authorization=authorization,
                    execution_store=execution_store,
                    sandbox_wait=sandbox_wait,
                    ledgers=ledgers,
                )
            elif job["kind"] == "prepare_packet":
                outcome = _prepare_packet(store, job, plan, lease_token)
            else:
                raise RunError("invalid_job_kind")
        _finish(store, job_id, lease_token, "succeeded", outcome=outcome)
    except KeyboardInterrupt:
        _interrupted(store, job_id, lease_token)
    except RunError as exc:
        if exc.reason != "job_lease_lost":
            _finish(store, job_id, lease_token, "failed", failure_reason=exc.reason)
    except Exception:
        _finish(
            store, job_id, lease_token, "failed", failure_reason="experiment_worker_internal_error"
        )
    with store.reading() as conn:
        return store.job(conn, job_id)


def _finish(store, job_id, lease_token, status, *, outcome=None, failure_reason=None):
    try:
        with store.transaction() as conn:
            store.verify_lease(conn, job_id, lease_token)
            job = store.job(conn, job_id)
            store.set_job_status(
                conn,
                job,
                status,
                outcome=outcome,
                failure_reason=failure_reason,
                finished_at=now(),
                lease_token=None,
                lease_until=None,
            )
            if job["task_id"]:
                task = store.task(conn, job["task_id"])
                if status == "failed" and task["status"] in ("scheduled", "running"):
                    store.set_task_status(conn, task, "failed")
            if job["kind"] == "analyze_plan" and status == "failed":
                run = store.run_for_job(conn, job_id)
                if run and run["status"] == "running":
                    store.update_run(
                        conn,
                        run["id"],
                        status="failed",
                        failure_reason=failure_reason,
                        finished_at=now(),
                    )
    except RunError as exc:
        if exc.reason != "job_lease_lost":
            raise


def _interrupted(store, job_id, lease_token):
    """A terminated worker requeues once (deterministic work) or fails; nothing is lost."""
    try:
        with store.transaction() as conn:
            store.verify_lease(conn, job_id, lease_token)
            job = store.job(conn, job_id)
            run = store.run_for_job(conn, job_id) if job["kind"] == "analyze_plan" else None
            if run and run["status"] == "running":
                store.update_run(
                    conn,
                    run["id"],
                    status="failed",
                    failure_reason="controller_interrupted",
                    finished_at=now(),
                )
            if job["attempts"] < job["max_attempts"]:
                store.set_job_status(conn, job, "scheduled", lease_token=None, lease_until=None)
                store.append_job_event(conn, job, "interrupted_requeued", attempt=job["attempts"])
            else:
                store.set_job_status(
                    conn,
                    job,
                    "failed",
                    failure_reason="controller_interrupted",
                    finished_at=now(),
                    lease_token=None,
                    lease_until=None,
                )
                if job["task_id"]:
                    task = store.task(conn, job["task_id"])
                    if task["status"] in ("scheduled", "running"):
                        store.set_task_status(conn, task, "failed")
    except RunError as exc:
        if exc.reason != "job_lease_lost":
            raise


def _analyze(
    store,
    job,
    plan,
    lease_token,
    *,
    runner,
    provider,
    authorization,
    execution_store,
    sandbox_wait,
    ledgers,
):
    payload = job["payload"]
    spec = plan["spec"]
    if plan["version"] != job["plan_version"] or plan_hash(spec) != plan["sha256"]:
        raise RunError("plan_version_conflict")
    if payload.get("plan_sha256") != plan["sha256"]:
        raise RunError("plan_version_conflict")
    script = program_bytes()
    digest = sha256(script)
    if payload.get("program_sha256") != digest:
        raise RunError("analysis_program_changed")
    manifest = store.dataset(plan["dataset_id"])
    if manifest["raw"]["sha256"] != payload.get("dataset_raw_sha256"):
        raise RunError("dataset_changed")
    task_input = analysis_task_input(store.dataset_input(manifest), spec)
    input_sha256 = sha256(task_input)
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], lease_token)
        existing = store.run_for_job(conn, job["id"])
        if existing and existing["status"] == "succeeded":
            raise RunError("run_already_completed")
        run_id = (
            store.insert_run(
                conn,
                owner=job["owner"],
                plan=plan,
                job=job,
                program_sha256=digest,
                input_sha256=input_sha256,
            )
            if existing is None
            else existing["id"]
        )
        if existing is not None:
            store.update_run(conn, run_id, status="running", failure_reason=None, finished_at=None)
        store.heartbeat(conn, job, lease_token, LEASE_SECONDS, stage="preparing")
    runner = runner or docker_runner()

    def checker(actual):
        try:
            validate_result(
                actual,
                manifest=manifest,
                spec=spec,
                input_sha256=input_sha256,
                program_sha256=digest,
            )
        except Rejected:
            raise
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise Rejected("analysis_result_malformed") from exc

    deadline = time.monotonic() + sandbox_wait
    while True:
        try:
            with serial_lock(execution_store):
                with store.transaction() as conn:
                    store.heartbeat(conn, job, lease_token, LEASE_SECONDS, stage="executing")
                runner.check_ready()
                _, execution = execute(
                    runner,
                    Task(script, task_input),
                    {"contract": ANALYSIS_VALIDATION, "plan_sha256": plan["sha256"]},
                    scenario="experiment-analysis",
                    store=execution_store,
                    limits=ANALYSIS_LIMITS,
                    validator=checker,
                    validation=ANALYSIS_VALIDATION,
                    task_bytes=ANALYSIS_INPUT_BYTES,
                )
            break
        except RunError as exc:
            if exc.reason != "another_controller_is_active":
                raise
            if time.monotonic() >= deadline:
                raise RunError("sandbox_busy") from None
            time.sleep(0.5)
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], lease_token)
        store.update_run(conn, run_id, execution_id=execution["id"])
        store.heartbeat(conn, job, lease_token, LEASE_SECONDS, stage="validating")
    if execution["status"] == "interrupted":
        # A terminated worker requeues; any container it could not remove is cleaned by
        # the restarted API's startup recovery before the next dispatch.
        raise KeyboardInterrupt
    if not execution["cleanup"]["removed"]:
        raise RunError("cleanup_unverified")
    if execution["status"] != "succeeded":
        raise RunError(execution["failure_reason"] or "execution_failed")
    result_bytes = (execution_store / execution["id"] / "result.json").read_bytes()
    if sha256(result_bytes) != execution["validated_artifacts"][0]["sha256"]:
        raise RunError("saved_artifact_hash_mismatch")
    result = strict_json(result_bytes)
    reconciliation = validate_result(
        result, manifest=manifest, spec=spec, input_sha256=input_sha256, program_sha256=digest
    )
    metrics = derive_metrics(result, manifest, spec)
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], lease_token)
        artifact = store.save_artifact(
            conn,
            owner=job["owner"],
            kind="analysis_result",
            content=result_bytes,
            run_id=run_id,
            job_id=job["id"],
        )
        store.update_run(
            conn, run_id, artifact_id=artifact["id"], reconciliation=reconciliation, metrics=metrics
        )
        store.heartbeat(conn, job, lease_token, LEASE_SECONDS, stage="interpreting")
    interpretation, generation = interpret(
        mode=payload.get("mode", "deterministic"),
        metrics=metrics,
        manifest=manifest,
        spec=spec,
        question=spec["question"],
        receipt_dir=store.root / "generation" / run_id,
        provider=provider,
        authorization=authorization,
        **({"ledgers": ledgers} if ledgers else {}),
    )
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], lease_token)
        store.update_run(
            conn,
            run_id,
            status="succeeded",
            finished_at=now(),
            interpretation=interpretation,
            generation=generation,
        )
        proposal_id = None
        if interpretation["status"] == "succeeded" and not store.proposals(
            conn, job["owner"], plan["id"]
        ):
            content = validate_proposal(
                {
                    **interpretation["rendered"]["proposed_next_experiment"],
                    "scenario_assumptions": dict(EMPTY_ASSUMPTIONS),
                    "sample_size_inputs": dict(EMPTY_SAMPLE),
                    "notes": "",
                }
            )
            proposal = store.insert_proposal(
                conn,
                owner=job["owner"],
                plan_id=plan["id"],
                run_id=run_id,
                content=content,
                provenance=interpretation["provenance"],
                proposal_sha256=proposal_hash(content),
            )
            proposal_id = proposal["id"]
    return {
        "run_id": run_id,
        "execution_id": execution["id"],
        "artifact_id": artifact["id"],
        "artifact_sha256": artifact["sha256"],
        "interpretation_status": interpretation["status"],
        "interpretation_provenance": interpretation["provenance"],
        "proposal_id": proposal_id,
    }


def _prepare_packet(store, job, plan, lease_token):
    payload = job["payload"]
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], lease_token)
        task = store.task(conn, job["task_id"])
        if task["owner"] != job["owner"]:
            raise RunError("experiment_not_found")
        if task["status"] == "scheduled":
            store.set_task_status(conn, task, "running", job_id=job["id"])
        elif task["status"] != "running":
            raise RunError("task_not_scheduled")
        approval = task["approval"]
        if not approval or approval.get("sha256") != payload.get("approval_sha256"):
            raise RunError("approval_stale")
        proposal = store.proposal(conn, task["proposal_id"], job["owner"])
        latest = store.proposals(conn, job["owner"], plan["id"])[0]
        if (
            proposal["sha256"] != task["proposal_sha256"]
            or proposal["sha256"] != payload.get("proposal_sha256")
            or latest["version"] != proposal["version"]
        ):
            raise RunError("approval_stale")
        if plan["sha256"] != payload.get("plan_sha256") or plan["version"] != job["plan_version"]:
            raise RunError("plan_version_conflict")
        run = store.run(conn, task["run_id"], job["owner"])
        if run["status"] != "succeeded" or not run["artifact_id"]:
            raise RunError("analysis_not_available")
        artifact = store.artifact(conn, run["artifact_id"], job["owner"])
        if artifact["sha256"] != payload.get("artifact_sha256"):
            raise RunError("approval_stale")
        manifest = store.dataset(plan["dataset_id"], conn)
        store.heartbeat(conn, job, lease_token, LEASE_SECONDS, stage="assembling")
    packet = assemble_packet(
        task=task,
        proposal=proposal,
        run=run,
        artifact=artifact,
        manifest=manifest,
        plan=plan,
        interpretation=run["interpretation"],
    )
    document = json.dumps(
        {"packet": packet, "markdown": render_markdown(packet)}, sort_keys=True, ensure_ascii=False
    ).encode()
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], lease_token)
        saved = store.save_artifact(
            conn,
            owner=job["owner"],
            kind="experiment_packet",
            content=document,
            run_id=run["id"],
            job_id=job["id"],
        )
        task = store.task(conn, task["id"])
        store.set_task_status(conn, task, "ready_for_review", packet_artifact_id=saved["id"])
    return {
        "task_id": task["id"],
        "artifact_id": saved["id"],
        "artifact_sha256": saved["sha256"],
        "packet_status": packet["status"],
        "unresolved_inputs": packet["unresolved_inputs"],
        "model_call": False,
    }
