"""Versioned SQLite store for datasets, plans, runs, artifacts, proposals, tasks and jobs.

Parameterized SQL only, explicit immediate transactions, unique operation keys for every
idempotent request, owner hashes on every record and cross-owner reads answered as
not-found. Everything lives under ignored .local/experiments/ next to the existing
prospect and execution records, which are never touched.
"""

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from ..execution.artifacts import sha256, strict_json
from ..execution.controller import ROOT, atomic_json, now
from ..execution.runner import RunError
from ..web_jobs import bounded_file
from .contracts import JOB_KINDS, JOB_STATES, TASK_STATES, transition

SCHEMA_VERSION = 1
ARTIFACT_LIMIT = 262144
DDL = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS datasets (
  id TEXT PRIMARY KEY, raw_sha256 TEXT NOT NULL, manifest TEXT NOT NULL, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations (
  key TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, result_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, dataset_id TEXT NOT NULL REFERENCES datasets(id),
  version INTEGER NOT NULL, sha256 TEXT NOT NULL, spec TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS plan_versions (
  plan_id TEXT NOT NULL REFERENCES plans(id), version INTEGER NOT NULL, sha256 TEXT NOT NULL,
  spec TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (plan_id, version)
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL,
  plan_id TEXT NOT NULL REFERENCES plans(id), plan_version INTEGER NOT NULL,
  task_id TEXT, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
  operation_key TEXT NOT NULL UNIQUE, due_at TEXT NOT NULL, status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
  lease_token TEXT, lease_until TEXT, created_at TEXT NOT NULL, started_at TEXT,
  finished_at TEXT, failure_reason TEXT, outcome TEXT, events TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_due ON jobs (status, due_at);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, plan_id TEXT NOT NULL REFERENCES plans(id),
  plan_version INTEGER NOT NULL, plan_sha256 TEXT NOT NULL,
  job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id), attempt INTEGER NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL, finished_at TEXT, failure_reason TEXT,
  execution_id TEXT, artifact_id TEXT, program_sha256 TEXT, input_sha256 TEXT,
  reconciliation TEXT, metrics TEXT, interpretation TEXT, generation TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, sha256 TEXT NOT NULL,
  bytes INTEGER NOT NULL, path TEXT NOT NULL, run_id TEXT, job_id TEXT UNIQUE,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, plan_id TEXT NOT NULL REFERENCES plans(id),
  run_id TEXT NOT NULL, version INTEGER NOT NULL, sha256 TEXT NOT NULL, content TEXT NOT NULL,
  provenance TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE (plan_id, version)
);
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY, owner TEXT NOT NULL, plan_id TEXT NOT NULL REFERENCES plans(id),
  run_id TEXT NOT NULL, proposal_id TEXT NOT NULL, proposal_version INTEGER NOT NULL,
  proposal_sha256 TEXT NOT NULL, title TEXT NOT NULL, assignee_label TEXT NOT NULL,
  proposed_action TEXT NOT NULL, due_date TEXT, status TEXT NOT NULL, approval TEXT,
  job_id TEXT, packet_artifact_id TEXT, completion TEXT, created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, events TEXT NOT NULL
);
"""
JSON_COLUMNS = {
    "manifest",
    "spec",
    "payload",
    "outcome",
    "events",
    "reconciliation",
    "metrics",
    "interpretation",
    "generation",
    "content",
    "approval",
    "completion",
}


def new_id():
    return uuid.uuid4().hex


def check_id(value, reason="experiment_not_found"):
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise RunError(reason)
    return value


def record(row):
    if row is None:
        return None
    data = dict(row)
    for key in JSON_COLUMNS:
        if key in data and isinstance(data[key], str):
            data[key] = json.loads(data[key])
    return data


def dump(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class Store:
    def __init__(self, root=None):
        self.root = Path(
            root or os.environ.get("PROOFDESK_EXPERIMENT_STORE", ROOT / ".local/experiments")
        )
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.root / "artifacts").mkdir(exist_ok=True, mode=0o700)
        self.database = self.root / "experiments.sqlite"
        connection = self.connect()
        try:
            connection.executescript(DDL)  # executescript commits on its own.
        finally:
            connection.close()
        with self.transaction() as conn:
            saved = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
            if saved is None:
                conn.execute(
                    "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            elif int(saved[0]) != SCHEMA_VERSION:
                raise RunError("experiment_store_version_mismatch")

    def connect(self):
        connection = sqlite3.connect(str(self.database), timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @contextmanager
    def transaction(self):
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    @contextmanager
    def reading(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    # Datasets -------------------------------------------------------------------------
    def save_dataset(self, manifest):
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO datasets (id, raw_sha256, manifest, imported_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET raw_sha256 = excluded.raw_sha256, "
                "manifest = excluded.manifest, imported_at = excluded.imported_at",
                (
                    manifest["id"],
                    manifest["raw"]["sha256"],
                    dump(manifest),
                    manifest["imported_at"],
                ),
            )
        return manifest

    def datasets(self):
        with self.reading() as conn:
            rows = conn.execute("SELECT manifest FROM datasets ORDER BY id").fetchall()
        return [json.loads(row["manifest"]) for row in rows]

    def dataset(self, dataset_id, conn=None):
        if not isinstance(dataset_id, str) or not re.fullmatch(r"[a-z0-9-]{1,40}", dataset_id):
            raise RunError("dataset_not_found")
        query = "SELECT manifest FROM datasets WHERE id = ?"
        if conn is None:
            with self.reading() as conn:
                row = conn.execute(query, (dataset_id,)).fetchone()
        else:
            row = conn.execute(query, (dataset_id,)).fetchone()
        if row is None:
            raise RunError("dataset_not_found")
        return json.loads(row["manifest"])

    def dataset_input(self, manifest):
        path = self.root / manifest["analysis_input"]["path"]
        data = bounded_file(path, 2 * 1024 * 1024)
        if sha256(data) != manifest["analysis_input"]["sha256"]:
            raise RunError("dataset_input_hash_mismatch")
        return data

    # Operations (idempotency) ---------------------------------------------------------
    def operation(self, conn, owner, kind, request_id):
        if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
            raise RunError("invalid_request_id")
        key = f"{owner}:{kind}:{request_id}"
        row = conn.execute("SELECT result_id FROM operations WHERE key = ?", (key,)).fetchone()
        return key, (row["result_id"] if row else None)

    def record_operation(self, conn, key, owner, kind, result_id):
        conn.execute(
            "INSERT INTO operations (key, owner, kind, result_id, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (key, owner, kind, result_id, now()),
        )

    # Plans ----------------------------------------------------------------------------
    def insert_plan(self, conn, owner, spec, plan_sha256):
        plan_id = new_id()
        stamp = now()
        conn.execute(
            "INSERT INTO plans (id, owner, dataset_id, version, sha256, spec, created_at,"
            " updated_at) VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
            (plan_id, owner, spec["dataset_id"], plan_sha256, dump(spec), stamp, stamp),
        )
        conn.execute(
            "INSERT INTO plan_versions (plan_id, version, sha256, spec, created_at)"
            " VALUES (?, 1, ?, ?, ?)",
            (plan_id, plan_sha256, dump(spec), stamp),
        )
        return plan_id

    def plan(self, conn, plan_id, owner):
        row = conn.execute(
            "SELECT * FROM plans WHERE id = ? AND owner = ?", (check_id(plan_id), owner)
        ).fetchone()
        if row is None:
            raise RunError("experiment_not_found")
        return record(row)

    def plans(self, conn, owner):
        rows = conn.execute(
            "SELECT * FROM plans WHERE owner = ? ORDER BY created_at DESC", (owner,)
        ).fetchall()
        return [record(r) for r in rows]

    def count(self, conn, table, owner, **where):
        clauses = ["owner = ?"]
        values = [owner]
        for key, value in where.items():
            clauses.append(f"{key} = ?")
            values.append(value)
        query = f"SELECT COUNT(*) FROM {table} WHERE " + " AND ".join(clauses)  # noqa: S608
        return conn.execute(query, values).fetchone()[0]

    # Jobs -----------------------------------------------------------------------------
    def insert_job(
        self,
        conn,
        *,
        owner,
        kind,
        plan,
        payload,
        due_at,
        operation_key,
        task_id=None,
        max_attempts=2,
    ):
        if kind not in JOB_KINDS:
            raise RunError("invalid_job_kind")
        job_id = new_id()
        stamp = now()
        conn.execute(
            "INSERT INTO jobs (id, owner, kind, plan_id, plan_version, task_id, payload,"
            " payload_sha256, operation_key, due_at, status, attempts, max_attempts, created_at,"
            " events) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', 0, ?, ?, ?)",
            (
                job_id,
                owner,
                kind,
                plan["id"],
                plan["version"],
                task_id,
                dump(payload),
                sha256(dump(payload).encode()),
                operation_key,
                due_at,
                max_attempts,
                stamp,
                dump([{"stage": "scheduled", "at": stamp, "due_at": due_at}]),
            ),
        )
        return job_id

    def job(self, conn, job_id, owner=None):
        if owner is None:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (check_id(job_id),)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ? AND owner = ?", (check_id(job_id), owner)
            ).fetchone()
        if row is None:
            raise RunError("experiment_not_found")
        return record(row)

    def jobs(self, conn, owner, plan_id=None):
        if plan_id:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE owner = ? AND plan_id = ? ORDER BY created_at DESC",
                (owner, plan_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE owner = ? ORDER BY created_at DESC", (owner,)
            ).fetchall()
        return [record(r) for r in rows]

    def append_job_event(self, conn, job, stage, **extra):
        events = job["events"] + [{"stage": stage, "at": now(), **extra}]
        conn.execute("UPDATE jobs SET events = ? WHERE id = ?", (dump(events[-50:]), job["id"]))
        job["events"] = events[-50:]

    def set_job_status(self, conn, job, status, **fields):
        if status not in JOB_STATES:
            raise RunError("invalid_job_status")
        transition("job", job["status"], status)
        assignments = ["status = ?"]
        values = [status]
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            values.append(dump(value) if key in JSON_COLUMNS and value is not None else value)
        values.append(job["id"])
        conn.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?", values)  # noqa: S608
        job["status"] = status
        job.update(fields)
        self.append_job_event(conn, job, status)

    def claim_due(self, conn, moment, lease_token, lease_seconds, *, max_running=1):
        """Claim at most one due job atomically; returns the claimed job or None."""
        running = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'running'").fetchone()[0]
        if running >= max_running:
            return None
        row = conn.execute(
            "SELECT * FROM jobs WHERE status = 'scheduled' AND due_at <= ?"
            " ORDER BY due_at, created_at LIMIT 1",
            (moment,),
        ).fetchone()
        if row is None:
            return None
        job = record(row)
        lease_until = _later(moment, lease_seconds)
        changed = conn.execute(
            "UPDATE jobs SET status = 'running', attempts = attempts + 1, lease_token = ?,"
            " lease_until = ?, started_at = COALESCE(started_at, ?)"
            " WHERE id = ? AND status = 'scheduled'",
            (lease_token, lease_until, moment, job["id"]),
        ).rowcount
        if changed != 1:
            return None
        job.update(
            status="running",
            attempts=job["attempts"] + 1,
            lease_token=lease_token,
            lease_until=lease_until,
            started_at=job["started_at"] or moment,
        )
        self.append_job_event(
            conn, job, "claimed", attempt=job["attempts"], lease_until=lease_until
        )
        return job

    def verify_lease(self, conn, job_id, lease_token):
        row = conn.execute(
            "SELECT status, lease_token, lease_until FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if (
            row is None
            or row["status"] != "running"
            or row["lease_token"] != lease_token
            or (row["lease_until"] or "") < now()
        ):
            raise RunError("job_lease_lost")

    def heartbeat(self, conn, job, lease_token, lease_seconds, stage=None):
        self.verify_lease(conn, job["id"], lease_token)
        lease_until = _later(now(), lease_seconds)
        conn.execute("UPDATE jobs SET lease_until = ? WHERE id = ?", (lease_until, job["id"]))
        job["lease_until"] = lease_until
        if stage:
            self.append_job_event(conn, job, stage)

    def expire_leases(self, conn, moment, *, job_ids=None):
        """Requeue or fail running jobs whose lease expired or whose worker is known lost."""
        rows = conn.execute("SELECT * FROM jobs WHERE status = 'running'").fetchall()
        changed = []
        for row in rows:
            job = record(row)
            lost = (
                job["id"] in job_ids if job_ids is not None else (job["lease_until"] or "") < moment
            )
            if not lost:
                continue
            if job["attempts"] < job["max_attempts"]:
                self.set_job_status(
                    conn, job, "scheduled", lease_token=None, lease_until=None, failure_reason=None
                )
                self.append_job_event(
                    conn, job, "requeued_after_lost_worker", attempt=job["attempts"]
                )
            else:
                self.set_job_status(
                    conn,
                    job,
                    "failed",
                    lease_token=None,
                    lease_until=None,
                    failure_reason="worker_abandoned",
                    finished_at=moment,
                )
            changed.append(job)
        return changed

    # Runs -----------------------------------------------------------------------------
    def insert_run(self, conn, *, owner, plan, job, program_sha256, input_sha256):
        run_id = new_id()
        conn.execute(
            "INSERT INTO runs (id, owner, plan_id, plan_version, plan_sha256, job_id, attempt,"
            " status, created_at, program_sha256, input_sha256, generation) VALUES"
            " (?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?, ?)",
            (
                run_id,
                owner,
                plan["id"],
                plan["version"],
                plan["sha256"],
                job["id"],
                job["attempts"],
                now(),
                program_sha256,
                input_sha256,
                dump({"mode": None, "model": None, "receipts": {}, "diagnostics": []}),
            ),
        )
        return run_id

    def update_run(self, conn, run_id, **fields):
        assignments, values = [], []
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            values.append(dump(value) if key in JSON_COLUMNS and value is not None else value)
        values.append(run_id)
        conn.execute(f"UPDATE runs SET {', '.join(assignments)} WHERE id = ?", values)  # noqa: S608

    def run_for_job(self, conn, job_id):
        return record(conn.execute("SELECT * FROM runs WHERE job_id = ?", (job_id,)).fetchone())

    def run(self, conn, run_id, owner):
        row = conn.execute(
            "SELECT * FROM runs WHERE id = ? AND owner = ?", (check_id(run_id), owner)
        ).fetchone()
        if row is None:
            raise RunError("experiment_not_found")
        return record(row)

    def runs(self, conn, owner, plan_id):
        rows = conn.execute(
            "SELECT * FROM runs WHERE owner = ? AND plan_id = ? ORDER BY created_at DESC",
            (owner, plan_id),
        ).fetchall()
        return [record(r) for r in rows]

    # Artifacts ------------------------------------------------------------------------
    def save_artifact(self, conn, *, owner, kind, content, run_id=None, job_id=None):
        """Write once per job; a duplicate dispatch cannot create a second final artifact."""
        if len(content) > ARTIFACT_LIMIT:
            raise RunError("artifact_too_large")
        if job_id is not None:
            existing = conn.execute(
                "SELECT id FROM artifacts WHERE job_id = ?", (job_id,)
            ).fetchone()
            if existing is not None:
                raise RunError("artifact_already_saved")
        artifact_id = new_id()
        path = self.root / "artifacts" / f"{artifact_id}.json"
        atomic_json(path, strict_json(content))
        saved = path.read_bytes()
        conn.execute(
            "INSERT INTO artifacts (id, owner, kind, sha256, bytes, path, run_id, job_id,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                artifact_id,
                owner,
                kind,
                sha256(saved),
                len(saved),
                str(path.relative_to(self.root)),
                run_id,
                job_id,
                now(),
            ),
        )
        return {"id": artifact_id, "kind": kind, "sha256": sha256(saved), "bytes": len(saved)}

    def artifact(self, conn, artifact_id, owner):
        row = conn.execute(
            "SELECT * FROM artifacts WHERE id = ? AND owner = ?", (check_id(artifact_id), owner)
        ).fetchone()
        if row is None:
            raise RunError("experiment_not_found")
        meta = dict(row)
        data = bounded_file(self.root / meta["path"], ARTIFACT_LIMIT)
        if sha256(data) != meta["sha256"]:
            raise RunError("saved_artifact_hash_mismatch")
        meta["content"] = strict_json(data)
        return meta

    # Proposals ------------------------------------------------------------------------
    def insert_proposal(
        self, conn, *, owner, plan_id, run_id, content, provenance, proposal_sha256
    ):
        latest = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM proposals WHERE plan_id = ?", (plan_id,)
        ).fetchone()[0]
        proposal_id = new_id()
        conn.execute(
            "INSERT INTO proposals (id, owner, plan_id, run_id, version, sha256, content,"
            " provenance, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                proposal_id,
                owner,
                plan_id,
                run_id,
                latest + 1,
                proposal_sha256,
                dump(content),
                provenance,
                now(),
            ),
        )
        return record(
            conn.execute("SELECT * FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        )

    def proposals(self, conn, owner, plan_id):
        rows = conn.execute(
            "SELECT * FROM proposals WHERE owner = ? AND plan_id = ? ORDER BY version DESC",
            (owner, plan_id),
        ).fetchall()
        return [record(r) for r in rows]

    def proposal(self, conn, proposal_id, owner):
        row = conn.execute(
            "SELECT * FROM proposals WHERE id = ? AND owner = ?", (check_id(proposal_id), owner)
        ).fetchone()
        if row is None:
            raise RunError("experiment_not_found")
        return record(row)

    # Tasks ----------------------------------------------------------------------------
    def insert_task(self, conn, *, owner, plan_id, run_id, proposal, fields):
        task_id = new_id()
        stamp = now()
        conn.execute(
            "INSERT INTO tasks (id, owner, plan_id, run_id, proposal_id, proposal_version,"
            " proposal_sha256, title, assignee_label, proposed_action, due_date, status,"
            " created_at, updated_at, events)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_review', ?, ?, ?)",
            (
                task_id,
                owner,
                plan_id,
                run_id,
                proposal["id"],
                proposal["version"],
                proposal["sha256"],
                fields["title"],
                fields["assignee_label"],
                fields["proposed_action"],
                fields["due_date"],
                stamp,
                stamp,
                dump([{"stage": "pending_review", "at": stamp}]),
            ),
        )
        return task_id

    def task(self, conn, task_id, owner=None):
        if owner is None:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (check_id(task_id),)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND owner = ?", (check_id(task_id), owner)
            ).fetchone()
        if row is None:
            raise RunError("experiment_not_found")
        return record(row)

    def tasks(self, conn, owner, plan_id=None):
        if plan_id:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE owner = ? AND plan_id = ? ORDER BY created_at DESC",
                (owner, plan_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE owner = ? ORDER BY created_at DESC", (owner,)
            ).fetchall()
        return [record(r) for r in rows]

    def append_task_note(self, conn, task, note):
        events = task["events"] + [{"stage": "note", "at": now(), "note": note}]
        conn.execute("UPDATE tasks SET events = ? WHERE id = ?", (dump(events[-50:]), task["id"]))
        task["events"] = events[-50:]

    def set_task_status(self, conn, task, status, **fields):
        if status not in TASK_STATES:
            raise RunError("invalid_task_status")
        transition("task", task["status"], status)
        stamp = now()
        events = task["events"] + [{"stage": status, "at": stamp}]
        assignments = ["status = ?", "updated_at = ?", "events = ?"]
        values = [status, stamp, dump(events[-50:])]
        for key, value in fields.items():
            assignments.append(f"{key} = ?")
            values.append(dump(value) if key in JSON_COLUMNS and value is not None else value)
        values.append(task["id"])
        conn.execute(f"UPDATE tasks SET {', '.join(assignments)} WHERE id = ?", values)  # noqa: S608
        task.update(status=status, updated_at=stamp, events=events[-50:], **fields)
        return task


def _later(moment, seconds):
    from datetime import datetime, timedelta

    base = datetime.fromisoformat(moment)
    return (base + timedelta(seconds=seconds)).isoformat()
