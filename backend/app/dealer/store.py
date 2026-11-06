"""Session-scoped dealer records, using the existing transactional job/lease store."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from ..execution.artifacts import sha256
from ..execution.controller import ROOT, now
from ..execution.runner import RunError
from ..experiments.store import Store, dump, new_id
from .ingestion import sample_group, validate_group

DDL = """
CREATE TABLE IF NOT EXISTS dealer_groups (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL UNIQUE, content TEXT NOT NULL,
 sha256 TEXT NOT NULL, plan_id TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dealer_imports (
 owner TEXT NOT NULL, kind TEXT NOT NULL, content TEXT NOT NULL, report TEXT NOT NULL,
 PRIMARY KEY(owner,kind));
CREATE TABLE IF NOT EXISTS dealer_followups (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, source TEXT NOT NULL, rooftop_id TEXT NOT NULL,
 lead_id TEXT NOT NULL, snapshot TEXT NOT NULL, content TEXT NOT NULL,
 version INTEGER NOT NULL, sha256 TEXT NOT NULL, status TEXT NOT NULL, approval TEXT,
 UNIQUE(owner,source,lead_id));
CREATE TABLE IF NOT EXISTS dealer_schedules (
 owner TEXT PRIMARY KEY, enabled INTEGER NOT NULL, next_due TEXT, expires_at TEXT,
 last_error TEXT);
"""


class DealerStore(Store):
    def __init__(self, root=None):
        super().__init__(root or os.environ.get("SALESDESK_DEALER_STORE", ROOT / ".local/dealer"))
        with self.reading() as conn:
            conn.executescript(DDL)

    def group(self, conn, owner):
        row = conn.execute("SELECT * FROM dealer_groups WHERE owner=?", (owner,)).fetchone()
        if row is None:
            raise RunError("dealer_not_found")
        return {**dict(row), "content": json.loads(row["content"])}

    def seed(self, owner):
        with self.reading() as conn:
            if conn.execute("SELECT 1 FROM dealer_groups WHERE owner=?", (owner,)).fetchone():
                return self.group(conn, owner)
        group = sample_group(datetime.now(UTC))
        return self.save_group(owner, group, only_if_absent=True)

    def save_group(self, owner, content, *, only_if_absent=False):
        serialized = dump(content)
        with self.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM dealer_groups WHERE owner=?", (owner,)
            ).fetchone()
            if only_if_absent and existing:
                return self.group(conn, owner)
            if (
                not existing
                and conn.execute("SELECT COUNT(*) FROM dealer_groups").fetchone()[0] >= 200
            ):
                raise RunError("dealer_quota_reached")
            if (
                existing
                and conn.execute(
                    "SELECT 1 FROM jobs WHERE owner=? AND status IN ('scheduled','running')",
                    (owner,),
                ).fetchone()
            ):
                raise RunError("dealer_review_active")
            gid = existing["id"] if existing else new_id()
            conn.execute(
                "INSERT INTO dealer_groups VALUES(?,?,?,?,NULL,?) "
                "ON CONFLICT(owner) DO UPDATE SET content=excluded.content, "
                "sha256=excluded.sha256, plan_id=NULL",
                (gid, owner, serialized, sha256(serialized.encode()), now()),
            )
            return self.group(conn, owner)

    def stage_import(self, owner, kind, rows, report):
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO dealer_imports VALUES(?,?,?,?) "
                "ON CONFLICT(owner,kind) DO UPDATE SET content=excluded.content, "
                "report=excluded.report",
                (owner, kind, dump(rows), dump(report)),
            )
        return report

    def finish_import(self, owner):
        with self.reading() as conn:
            staged = conn.execute("SELECT * FROM dealer_imports WHERE owner=?", (owner,)).fetchall()
        if {r["kind"] for r in staged} != {"rooftops", "inventory", "leads"}:
            raise RunError("csv_three_files_required")
        reports = [json.loads(r["report"]) for r in staged]
        if any(r["rejected"] for r in reports):
            raise RunError("csv_validation_failed")
        content = validate_group(**{r["kind"]: json.loads(r["content"]) for r in staged})
        content.update(
            group="Your dealer group",
            data_label="CSV import",
            synthetic=False,
            reference_time=now(),
            floorplan_daily_rate=8.0,
            match_distance_miles=250,
            validation=reports,
        )
        self.save_group(owner, content)
        with self.transaction() as conn:
            conn.execute("DELETE FROM dealer_imports WHERE owner=?", (owner,))
        return {"imported": True, "validation": reports, "data_label": "CSV import"}

    def claim_due(self, conn, moment, lease_token, lease_seconds, *, max_running=1):
        # Roll-up waits durably without consuming a worker or a lease. A restart
        # cannot finish the parent before all children reach a terminal state.
        parents = conn.execute(
            "SELECT * FROM jobs WHERE kind='dealer_rollup' AND status='scheduled'"
        ).fetchall()
        waiting = []
        for row in parents:
            pending = conn.execute(
                "SELECT 1 FROM jobs WHERE json_extract(payload,'$.parent_id')=? "
                "AND status IN ('scheduled','running') LIMIT 1",
                (row["id"],),
            ).fetchone()
            if pending:
                waiting.append((row["id"], row["due_at"]))
                conn.execute("UPDATE jobs SET due_at=? WHERE id=?", ("9999-01-01", row["id"]))
        job = super().claim_due(conn, moment, lease_token, lease_seconds, max_running=max_running)
        for jid, due in waiting:
            conn.execute("UPDATE jobs SET due_at=? WHERE id=?", (due, jid))
        return job

    def ensure_plan(self, conn, group):
        if group["plan_id"]:
            return self.plan(conn, group["plan_id"], group["owner"])
        spec = dict(dataset_id="dealer-group", group_sha256=group["sha256"])
        conn.execute(
            "INSERT OR IGNORE INTO datasets VALUES(?,?,?,?)",
            ("dealer-group", group["sha256"], dump({"id": "dealer-group"}), now()),
        )
        pid = self.insert_plan(conn, group["owner"], spec, sha256(dump(spec).encode()))
        conn.execute("UPDATE dealer_groups SET plan_id=? WHERE id=?", (pid, group["id"]))
        return self.plan(conn, pid, group["owner"])

    def start_review(self, owner, request_id, *, mode="deterministic"):
        with self.transaction() as conn:
            key, prior = self.operation(conn, owner, "dealer_review", request_id)
            if prior:
                return self.job(conn, prior, owner)
            group = self.group(conn, owner)
            existing = conn.execute(
                "SELECT id FROM jobs WHERE owner=? AND kind='dealer_rollup' "
                "AND status IN ('scheduled','running')",
                (owner,),
            ).fetchone()
            if existing:
                return self.job(conn, existing["id"], owner)
            if self.count(conn, "jobs", owner, kind="dealer_rollup") >= 6:
                raise RunError("dealer_quota_reached")
            if (
                conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
                + len(group["content"]["rooftops"])
                + 1
                > 5000
            ):
                raise RunError("dealer_quota_reached")
            plan = self.ensure_plan(conn, group)
            stamp = now()
            previous = self.latest_review(conn, owner, group["sha256"])
            payload = dict(
                group_sha256=group["sha256"],
                mode=mode,
                program_sha256=sha256(Path(__file__).with_name("analysis_program.py").read_bytes()),
                previous_parent_id=previous["id"]
                if previous and previous["status"] == "succeeded"
                else None,
            )
            parent = self.insert_job(
                conn,
                owner=owner,
                kind="dealer_rollup",
                plan=plan,
                payload=payload,
                due_at=stamp,
                operation_key=key,
            )
            for roof in group["content"]["rooftops"]:
                self.insert_job(
                    conn,
                    owner=owner,
                    kind="dealer_rooftop",
                    plan=plan,
                    payload=dict(**payload, rooftop_id=roof["id"], parent_id=parent),
                    due_at=stamp,
                    operation_key=key + ":" + roof["id"],
                )
            self.record_operation(conn, key, owner, "dealer_review", parent)
            return self.job(conn, parent, owner)

    def result(self, job):
        if not job.get("outcome") or not job["outcome"].get("result_path"):
            return None
        path = self.root / job["outcome"]["result_path"]
        raw = path.read_bytes()
        if sha256(raw) != job["outcome"]["result_sha256"]:
            raise RunError("saved_artifact_hash_mismatch")
        return json.loads(raw)

    def latest_review(self, conn, owner, group_sha256=None):
        row = conn.execute(
            "SELECT id FROM jobs WHERE owner=? AND kind='dealer_rollup' "
            "AND json_extract(payload,'$.group_sha256')=? ORDER BY created_at DESC LIMIT 1",
            (owner, group_sha256 or self.group(conn, owner)["sha256"]),
        ).fetchone()
        return self.job(conn, row["id"], owner) if row else None
