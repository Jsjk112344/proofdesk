"""Session-scoped dealer records, using the existing transactional job/lease store."""

import json
import os
from datetime import UTC, datetime

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
