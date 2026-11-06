"""Owner-facing operations: plans, runs, proposals, tasks, approvals, scheduling and views.

Every operation is scoped to the session owner hash, idempotent by request id, bounded by
quotas (stricter in public-demo mode) and refuses cross-owner access as not found.
Approval binds to the exact proposal version and analysis artifact hash; editing the
proposal invalidates any approval and cancels pending preparation work.
"""

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..execution.artifacts import sha256, strict_json
from ..execution.controller import STORE, now
from ..execution.runner import RunError
from ..web_jobs import bounded_file
from .contracts import (
    plan_hash,
    proposal_hash,
    validate_plan_spec,
    validate_proposal,
    validate_task_fields,
)
from .jobs import Scheduler, docker_recovery, program_sha256
from .reasoning import live_mode
from .store import Store, dump

PRIVATE_LIMITS = {
    "max_plans": 10,
    "max_runs": 20,
    "max_tasks": 20,
    "max_jobs": 60,
    "max_scheduled": 5,
    "max_total_jobs": 500,
    "due_horizon_seconds": 30 * 86400,
}
PUBLIC_LIMITS = {
    "max_plans": 3,
    "max_runs": 6,
    "max_tasks": 6,
    "max_jobs": 12,
    "max_scheduled": 3,
    "max_total_jobs": 200,
    "due_horizon_seconds": 86400,
}
ACTIVE_JOB = {"scheduled", "running"}


def parse_due(value, *, horizon_seconds):
    """UTC ISO-8601 due time; 'now' schedules immediately. Operational dates only."""
    moment = datetime.now(UTC)
    if value == "now" or value is None:
        return moment.isoformat()
    if not isinstance(value, str) or len(value) > 40:
        raise RunError("invalid_due_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RunError("invalid_due_at") from exc
    if parsed.tzinfo is None:
        raise RunError("invalid_due_at")
    parsed = parsed.astimezone(UTC)
    if parsed < moment - timedelta(minutes=5) or parsed > moment + timedelta(
        seconds=horizon_seconds
    ):
        raise RunError("due_at_out_of_range")
    return max(parsed, moment).isoformat()


class Experiments:
    def __init__(
        self,
        store=None,
        *,
        public_demo=None,
        launch=None,
        execution_store=None,
        scheduler_interval=2.0,
        recover="docker",
    ):
        self.store = store or Store()
        self.public_demo = (
            public_demo
            if public_demo is not None
            else os.environ.get("PROOFDESK_PUBLIC_DEMO", "0") == "1"
        )
        self.limits = dict(PUBLIC_LIMITS if self.public_demo else PRIVATE_LIMITS)
        self.execution_store = Path(execution_store or STORE)
        self.scheduler = Scheduler(
            self.store,
            launch=launch,
            interval=scheduler_interval,
            recover=docker_recovery(self.execution_store) if recover == "docker" else recover,
        )

    # Lifecycle --------------------------------------------------------------------
    def mode(self):
        return live_mode(self.public_demo)

    def reconcile(self):
        """Startup reconciliation: sandbox recovery, then lost-worker requeue or failure."""
        self.scheduler.reconcile(startup=True)

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.scheduler.stop()

    # Read views -------------------------------------------------------------------
    def datasets(self):
        return [self._dataset_view(m) for m in self.store.datasets()]

    def dataset(self, dataset_id):
        return self._dataset_view(self.store.dataset(dataset_id))

    @staticmethod
    def _dataset_view(manifest):
        view = {k: v for k, v in manifest.items() if k not in {"analysis_input"}}
        view["raw"] = {k: v for k, v in manifest["raw"].items() if k != "local_path"}
        view["analysis_input"] = {
            k: v for k, v in manifest["analysis_input"].items() if k != "path"
        }
        view["raw_rows_served"] = False
        return view

    def overview(self, owner):
        with self.store.reading() as conn:
            plans = self.store.plans(conn, owner)
            tasks = self.store.tasks(conn, owner)
            jobs = self.store.jobs(conn, owner)
            summaries = []
            for plan in plans:
                runs = self.store.runs(conn, owner, plan["id"])
                proposals = self.store.proposals(conn, owner, plan["id"])
                summaries.append(self._plan_summary(plan, runs, proposals, tasks, jobs))
        return {
            "datasets": self.datasets(),
            "plans": summaries,
            "tasks": [self._task_view(t) for t in tasks],
            "jobs": [self._job_view(j) for j in jobs],
            "generation_mode": self.mode(),
            "public_demo": self.public_demo,
            "limits": self.limits,
            "scheduler": {
                "last_error": self.scheduler.last_error,
                "last_recovery": self.scheduler.last_recovery,
                "lease_seconds": 120,
            },
        }

    @staticmethod
    def _plan_summary(plan, runs, proposals, tasks, jobs):
        latest = runs[0] if runs else None
        return {
            "id": plan["id"],
            "version": plan["version"],
            "sha256": plan["sha256"],
            "dataset_id": plan["dataset_id"],
            "title": plan["spec"]["title"],
            "question": plan["spec"]["question"],
            "comparison": plan["spec"]["comparison"],
            "created_at": plan["created_at"],
            "runs": len(runs),
            "latest_run": (
                {
                    "id": latest["id"],
                    "status": latest["status"],
                    "failure_reason": latest["failure_reason"],
                    "finished_at": latest["finished_at"],
                    "interpretation_status": (latest["interpretation"] or {}).get("status"),
                    "interpretation_provenance": (latest["interpretation"] or {}).get("provenance"),
                }
                if latest
                else None
            ),
            "proposal_version": proposals[0]["version"] if proposals else 0,
            "tasks": [t["status"] for t in tasks if t["plan_id"] == plan["id"]],
            "active_jobs": sum(
                1 for j in jobs if j["plan_id"] == plan["id"] and j["status"] in ACTIVE_JOB
            ),
        }

    def plan_detail(self, plan_id, owner):
        with self.store.reading() as conn:
            plan = self.store.plan(conn, plan_id, owner)
            runs = self.store.runs(conn, owner, plan["id"])
            proposals = self.store.proposals(conn, owner, plan["id"])
            tasks = self.store.tasks(conn, owner, plan["id"])
            jobs = self.store.jobs(conn, owner, plan["id"])
            manifest = self.store.dataset(plan["dataset_id"], conn)
        return {
            "plan": self._plan_view(plan),
            "dataset": self._dataset_view(manifest),
            "runs": [self._run_view(r) for r in runs],
            "proposals": [self._proposal_view(p) for p in proposals],
            "tasks": [self._task_view(t) for t in tasks],
            "jobs": [self._job_view(j) for j in jobs],
            "generation_mode": self.mode(),
            "program_sha256": program_sha256(),
        }

    @staticmethod
    def _plan_view(plan):
        return {k: v for k, v in plan.items() if k != "owner"}

    def _run_view(self, run):
        view = {k: v for k, v in run.items() if k != "owner"}
        view["execution"] = None
        if run.get("execution_id"):
            try:
                view["execution"] = self.execution_view(run["execution_id"])
            except RunError as exc:
                view["execution"] = {"id": run["execution_id"], "unavailable": exc.reason}
        return view

    @staticmethod
    def _proposal_view(proposal):
        return {k: v for k, v in proposal.items() if k != "owner"}

    @staticmethod
    def _task_view(task):
        return {k: v for k, v in task.items() if k != "owner"}

    @staticmethod
    def _job_view(job):
        hidden = {"owner", "lease_token"}
        return {k: v for k, v in job.items() if k not in hidden}

    def execution_view(self, execution_id):
        """Bounded, hash-checked view of a sandbox execution record (no raw input)."""
        if not re.fullmatch(r"[a-f0-9]{32}", execution_id or ""):
            raise RunError("execution_not_found")
        directory = self.execution_store / execution_id
        if not (directory / "record.json").is_file():
            raise RunError("execution_not_found")
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
            "started_at",
            "finished_at",
            "revision",
        }
        view = {k: v for k, v in evidence.items() if k in keys}
        view["runtime"] = (evidence.get("evidence") or {}).get("runtime")
        view["task_elapsed_seconds"] = (evidence.get("evidence") or {}).get("task_elapsed_seconds")
        view["log"] = None
        if (directory / "task.log").is_file():
            view["log"] = bounded_file(directory / "task.log", 16384).decode(errors="replace")
        return view

    def job_detail(self, job_id, owner):
        with self.store.reading() as conn:
            job = self.store.job(conn, job_id, owner)
        return self._job_view(job)

    def artifact_view(self, artifact_id, owner):
        with self.store.reading() as conn:
            artifact = self.store.artifact(conn, artifact_id, owner)
        return {k: v for k, v in artifact.items() if k not in {"owner", "path"}}

    def packet_markdown(self, artifact_id, owner):
        artifact = self.artifact_view(artifact_id, owner)
        if artifact["kind"] != "experiment_packet":
            raise RunError("experiment_not_found")
        return artifact["content"]["markdown"], artifact

    # Writes -----------------------------------------------------------------------
    def create_plan(self, owner, request_id, data):
        if not isinstance(data, dict) or "dataset_id" not in data:
            raise RunError("invalid_plan")
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "create_plan", request_id)
            if existing:
                return self._plan_view(self.store.plan(conn, existing, owner))
            manifest = self.store.dataset(data["dataset_id"], conn)
            spec = validate_plan_spec(
                {k: v for k, v in data.items() if k != "dataset_id"}, manifest
            )
            if self.store.count(conn, "plans", owner) >= self.limits["max_plans"]:
                raise RunError("experiment_quota_reached")
            plan_id = self.store.insert_plan(conn, owner, spec, plan_hash(spec))
            self.store.record_operation(conn, key, owner, "create_plan", plan_id)
            return self._plan_view(self.store.plan(conn, plan_id, owner))

    def run_now(self, plan_id, owner, request_id):
        """Queue an analysis job due immediately; the scheduler runs it like any due job."""
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "run_now", request_id)
            if existing:
                return self._job_view(self.store.job(conn, existing, owner))
            plan = self.store.plan(conn, plan_id, owner)
            manifest = self.store.dataset(plan["dataset_id"], conn)
            self._check_job_quota(conn, owner, kind="analyze_plan")
            if self.store.count(conn, "runs", owner) >= self.limits["max_runs"]:
                raise RunError("experiment_quota_reached")
            payload = {
                "plan_sha256": plan["sha256"],
                "dataset_raw_sha256": manifest["raw"]["sha256"],
                "program_sha256": program_sha256(),
                "mode": self.mode(),
            }
            job_id = self.store.insert_job(
                conn,
                owner=owner,
                kind="analyze_plan",
                plan=plan,
                payload=payload,
                due_at=now(),
                operation_key=key,
            )
            self.store.record_operation(conn, key, owner, "run_now", job_id)
            return self._job_view(self.store.job(conn, job_id, owner))

    def _check_job_quota(self, conn, owner, *, kind):
        if self.store.count(conn, "jobs", owner) >= self.limits["max_jobs"]:
            raise RunError("experiment_quota_reached")
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        if total >= self.limits["max_total_jobs"]:
            raise RunError("experiment_quota_reached")
        active = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE owner = ? AND status IN ('scheduled', 'running')",
            (owner,),
        ).fetchone()[0]
        if active >= self.limits["max_scheduled"]:
            raise RunError("experiment_queue_full")

    def save_proposal(self, plan_id, owner, request_id, data, *, base_version):
        """Create a new human-edited proposal version; approvals bound to older ones lapse."""
        content = validate_proposal(data)
        if type(base_version) is not int or base_version < 0:
            raise RunError("invalid_proposal")
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "save_proposal", request_id)
            if existing:
                return self._proposal_view(self.store.proposal(conn, existing, owner))
            plan = self.store.plan(conn, plan_id, owner)
            proposals = self.store.proposals(conn, owner, plan["id"])
            current_version = proposals[0]["version"] if proposals else 0
            if current_version != base_version:
                raise RunError("proposal_version_conflict")
            runs = [
                r for r in self.store.runs(conn, owner, plan["id"]) if r["status"] == "succeeded"
            ]
            if not runs:
                raise RunError("analysis_not_available")
            digest = proposal_hash(content)
            if proposals and proposals[0]["sha256"] == digest:
                self.store.record_operation(conn, key, owner, "save_proposal", proposals[0]["id"])
                return self._proposal_view(proposals[0])
            proposal = self.store.insert_proposal(
                conn,
                owner=owner,
                plan_id=plan["id"],
                run_id=runs[0]["id"],
                content=content,
                provenance="human_edited",
                proposal_sha256=digest,
            )
            self._invalidate_tasks(conn, owner, plan["id"], proposal["version"])
            self.store.record_operation(conn, key, owner, "save_proposal", proposal["id"])
            return self._proposal_view(proposal)

    def _invalidate_tasks(self, conn, owner, plan_id, new_version):
        """Editing the proposal clears approvals and cancels not-yet-run preparation."""
        for task in self.store.tasks(conn, owner, plan_id):
            if task["proposal_version"] >= new_version:
                continue
            if task["status"] in ("approved", "scheduled", "failed"):
                if task["job_id"]:
                    job = self.store.job(conn, task["job_id"], owner)
                    if job["status"] == "scheduled":
                        self.store.set_job_status(
                            conn,
                            job,
                            "cancelled",
                            failure_reason="approval_invalidated",
                            finished_at=now(),
                        )
                self.store.set_task_status(conn, task, "pending_review", approval=None, job_id=None)
                self.store.append_task_note(conn, task, "approval_invalidated_by_proposal_edit")

    def create_task(self, plan_id, owner, request_id, data):
        fields = validate_task_fields(data)
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "create_task", request_id)
            if existing:
                return self._task_view(self.store.task(conn, existing, owner))
            plan = self.store.plan(conn, plan_id, owner)
            proposals = self.store.proposals(conn, owner, plan["id"])
            if not proposals:
                raise RunError("proposal_required")
            runs = [
                r for r in self.store.runs(conn, owner, plan["id"]) if r["status"] == "succeeded"
            ]
            if not runs:
                raise RunError("analysis_not_available")
            if self.store.count(conn, "tasks", owner) >= self.limits["max_tasks"]:
                raise RunError("experiment_quota_reached")
            task_id = self.store.insert_task(
                conn,
                owner=owner,
                plan_id=plan["id"],
                run_id=runs[0]["id"],
                proposal=proposals[0],
                fields=fields,
            )
            self.store.record_operation(conn, key, owner, "create_task", task_id)
            return self._task_view(self.store.task(conn, task_id, owner))

    def approve_task(self, task_id, owner, request_id, *, proposal_sha256):
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "approve_task", request_id)
            if existing:
                return self._task_view(self.store.task(conn, existing, owner))
            task = self.store.task(conn, task_id, owner)
            proposals = self.store.proposals(conn, owner, task["plan_id"])
            # Approval always binds to the current proposal version, which the client
            # must name explicitly; an older or unknown hash is a version conflict.
            if not proposals or proposals[0]["sha256"] != proposal_sha256:
                raise RunError("proposal_version_conflict")
            run = self.store.run(conn, task["run_id"], owner)
            if run["status"] != "succeeded" or not run["artifact_id"]:
                raise RunError("analysis_not_available")
            artifact = self.store.artifact(conn, run["artifact_id"], owner)
            approval = {
                "approved_at": now(),
                "proposal_sha256": proposal_sha256,
                "proposal_version": proposals[0]["version"],
                "artifact_sha256": artifact["sha256"],
                "plan_sha256": self.store.plan(conn, task["plan_id"], owner)["sha256"],
                "task_fields_sha256": sha256(
                    dump(
                        {
                            k: task[k]
                            for k in ("title", "assignee_label", "proposed_action", "due_date")
                        }
                    ).encode()
                ),
            }
            approval["sha256"] = sha256(dump(approval).encode())
            self.store.set_task_status(
                conn,
                task,
                "approved",
                approval=approval,
                proposal_id=proposals[0]["id"],
                proposal_version=proposals[0]["version"],
                proposal_sha256=proposals[0]["sha256"],
            )
            self.store.record_operation(conn, key, owner, "approve_task", task["id"])
            return self._task_view(task)

    def schedule_task(self, task_id, owner, request_id, *, due_at):
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "schedule_task", request_id)
            if existing:
                return self._task_view(self.store.task(conn, existing, owner))
            task = self.store.task(conn, task_id, owner)
            if task["status"] not in ("approved", "failed") or not task["approval"]:
                raise RunError("task_not_approved")
            plan = self.store.plan(conn, task["plan_id"], owner)
            proposals = self.store.proposals(conn, owner, plan["id"])
            if not proposals or proposals[0]["sha256"] != task["approval"]["proposal_sha256"]:
                raise RunError("approval_stale")
            if plan["sha256"] != task["approval"]["plan_sha256"]:
                raise RunError("approval_stale")
            self._check_job_quota(conn, owner, kind="prepare_packet")
            due = parse_due(due_at, horizon_seconds=self.limits["due_horizon_seconds"])
            payload = {
                "task_id": task["id"],
                "approval_sha256": task["approval"]["sha256"],
                "proposal_sha256": task["approval"]["proposal_sha256"],
                "artifact_sha256": task["approval"]["artifact_sha256"],
                "plan_sha256": plan["sha256"],
            }
            job_id = self.store.insert_job(
                conn,
                owner=owner,
                kind="prepare_packet",
                plan=plan,
                payload=payload,
                due_at=due,
                operation_key=key,
                task_id=task["id"],
            )
            self.store.set_task_status(conn, task, "scheduled", job_id=job_id)
            self.store.record_operation(conn, key, owner, "schedule_task", task["id"])
            return self._task_view(task)

    def cancel_task(self, task_id, owner):
        with self.store.transaction() as conn:
            task = self.store.task(conn, task_id, owner)
            if task["status"] in ("completed", "cancelled"):
                return self._task_view(task)
            if task["job_id"]:
                job = self.store.job(conn, task["job_id"], owner)
                if job["status"] in ACTIVE_JOB:
                    self.store.set_job_status(
                        conn, job, "cancelled", failure_reason="task_cancelled", finished_at=now()
                    )
            self.store.set_task_status(conn, task, "cancelled")
            return self._task_view(task)

    def cancel_job(self, job_id, owner):
        with self.store.transaction() as conn:
            job = self.store.job(conn, job_id, owner)
            if job["status"] in ACTIVE_JOB:
                self.store.set_job_status(
                    conn, job, "cancelled", failure_reason="cancelled_by_owner", finished_at=now()
                )
                if job["task_id"]:
                    task = self.store.task(conn, job["task_id"], owner)
                    if task["status"] in ("scheduled", "running"):
                        self.store.set_task_status(conn, task, "cancelled")
            return self._job_view(job)

    def complete_task(self, task_id, owner, request_id, *, evidence_note):
        if not isinstance(evidence_note, str) or not 1 <= len(evidence_note.strip()) <= 1000:
            raise RunError("invalid_completion_evidence")
        with self.store.transaction() as conn:
            key, existing = self.store.operation(conn, owner, "complete_task", request_id)
            if existing:
                return self._task_view(self.store.task(conn, existing, owner))
            task = self.store.task(conn, task_id, owner)
            if task["status"] != "ready_for_review" or not task["packet_artifact_id"]:
                raise RunError("packet_not_ready")
            completion = {
                "completed_at": now(),
                "evidence_note": evidence_note.strip(),
                "packet_artifact_id": task["packet_artifact_id"],
                "by": "workspace_owner",
            }
            self.store.set_task_status(conn, task, "completed", completion=completion)
            self.store.record_operation(conn, key, owner, "complete_task", task["id"])
            return self._task_view(task)
