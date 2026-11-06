"""Exact-version approvals and human task exports. Nothing is sent to a customer."""

import csv
import io
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from ..execution.artifacts import sha256
from ..execution.controller import now
from ..execution.runner import RunError
from ..experiments.jobs import LEASE_SECONDS
from ..experiments.store import dump, new_id
from .contracts import rendered
from .reasoning import deterministic

FILES = {"follow-ups.md", "crm-tasks.csv", "transfer-requests.csv"}


def content_hash(content, snapshot, version):
    return sha256(dump(dict(content=content, snapshot=snapshot, version=version)).encode())


def followup(row):
    value = dict(row)
    for key in ("content", "snapshot", "approval"):
        if value[key] is not None:
            value[key] = json.loads(value[key])
    return value


def materialize(store, owner, source, result, group):
    with store.reading() as conn:
        if conn.execute(
            "SELECT 1 FROM dealer_followups WHERE owner=? AND source=? LIMIT 1", (owner, source)
        ).fetchone():
            return
    brief = result.get("brief") or {}
    if brief.get("status") != "succeeded":
        return
    model_rows = {row["lead_id"]: row for row in brief["rendered"]["follow_ups"]}
    with store.transaction() as conn:
        for lead in result["queue"]:
            if not lead["matches"]:
                continue
            snapshot = dict(lead=lead, unit=lead["matches"][0], data_label=group["data_label"])
            row = model_rows.get(lead["lead_id"])
            provenance = brief["provenance"] if row else "deterministic_template"
            if row is None:
                single = dict(result, queue=[lead])
                reading = deterministic("rooftop_brief", single, group)
                row = rendered(reading, single, group)["follow_ups"][0]
            content = {k: row[k] for k in ("reason", "sms", "email_subject", "email_body")}
            snapshot["provenance"] = provenance
            digest = content_hash(content, snapshot, 1)
            conn.execute(
                "INSERT OR IGNORE INTO dealer_followups VALUES(?,?,?,?,?,?,?,1,?,?,NULL)",
                (
                    new_id(),
                    owner,
                    source,
                    result["rooftop_id"],
                    lead["lead_id"],
                    dump(snapshot),
                    dump(content),
                    digest,
                    "pending",
                ),
            )


def list_followups(store, conn, owner, source):
    return [
        followup(row)
        for row in conn.execute(
            "SELECT * FROM dealer_followups WHERE owner=? AND source=? ORDER BY rowid",
            (owner, source),
        ).fetchall()
    ]


def read(store, conn, owner, fid):
    row = conn.execute(
        "SELECT * FROM dealer_followups WHERE owner=? AND id=?", (owner, fid)
    ).fetchone()
    if row is None:
        raise RunError("dealer_not_found")
    return followup(row)


def edit(store, owner, fid, base_sha256, content):
    if not isinstance(content, dict) or set(content) != {"sms", "email_subject", "email_body"}:
        raise RunError("invalid_followup_edit")
    for key, maximum in [("sms", 320), ("email_subject", 100), ("email_body", 1000)]:
        text = content[key]
        if not isinstance(text, str) or not 1 <= len(text) <= maximum or "\x00" in text:
            raise RunError("invalid_followup_edit")
    with store.transaction() as conn:
        saved = read(store, conn, owner, fid)
        if saved["sha256"] != base_sha256:
            raise RunError("approval_version_conflict")
        new = dict(saved["content"], **content)
        version = saved["version"] + 1
        digest = content_hash(new, saved["snapshot"], version)
        conn.execute(
            "UPDATE dealer_followups SET content=?,version=?,sha256=?,approval=NULL,"
            "status='pending' WHERE id=?",
            (dump(new), version, digest, fid),
        )
        return read(store, conn, owner, fid)


def approve(store, owner, rid, versions, request_id):
    if not isinstance(versions, list) or not 1 <= len(versions) <= 1000:
        raise RunError("invalid_followup_approval")
    with store.transaction() as conn:
        key, existing = store.operation(conn, owner, "dealer_approve", request_id)
        if existing:
            return store.job(conn, existing, owner)
        if store.count(conn, "jobs", owner, kind="dealer_handoff") >= 72:
            raise RunError("dealer_quota_reached")
        group = store.group(conn, owner)
        plan = store.ensure_plan(conn, group)
        rows = []
        seen = set()
        for expected in versions:
            if not isinstance(expected, dict) or set(expected) != {"id", "sha256", "version"}:
                raise RunError("invalid_followup_approval")
            saved = read(store, conn, owner, expected["id"])
            if (
                saved["rooftop_id"] != rid
                or saved["sha256"] != expected["sha256"]
                or saved["version"] != expected["version"]
                or saved["status"] == "skipped"
                or saved["id"] in seen
            ):
                raise RunError("approval_version_conflict")
            seen.add(saved["id"])
            rows.append(saved)
        for row in rows:
            receipt = dict(
                version=row["version"],
                sha256=row["sha256"],
                approved_at=now(),
                source=row["source"],
            )
            conn.execute(
                "UPDATE dealer_followups SET status='approved',approval=? WHERE id=?",
                (dump(receipt), row["id"]),
            )
        jid = store.insert_job(
            conn,
            owner=owner,
            kind="dealer_handoff",
            plan=plan,
            payload=dict(group_sha256=group["sha256"], rooftop_id=rid, versions=versions),
            due_at=now(),
            operation_key=key,
        )
        store.record_operation(conn, key, owner, "dealer_approve", jid)
        return store.job(conn, jid, owner)


def checked_rows(store, conn, job):
    rows = []
    for expected in job["payload"]["versions"]:
        saved = read(store, conn, job["owner"], expected["id"])
        if (
            saved["sha256"] != expected["sha256"]
            or saved["version"] != expected["version"]
            or not saved["approval"]
            or saved["status"] != "approved"
        ):
            raise RunError("approval_version_conflict")
        if saved["approval"]["sha256"] != saved["sha256"]:
            raise RunError("approval_version_conflict")
        rows.append(saved)
    return rows


def csv_export(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    for row in rows:
        # Protect spreadsheet import from formula cells in untrusted CSV or human edits.
        writer.writerow(
            [
                "'" + str(value) if str(value).lstrip().startswith(("=", "+", "-", "@")) else value
                for value in row
            ]
        )
    return stream.getvalue()


def prepare(store, job, token):
    from .jobs import save_result

    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], token)
        rows = checked_rows(store, conn, job)
        store.heartbeat(conn, job, token, LEASE_SECONDS, stage="preparing_on_vultr")
    today = datetime.now(ZoneInfo("America/Denver")).date().isoformat()
    markdown = ["# Approved follow-ups", "", "Tasks and drafts for salespeople. Nothing sent.", ""]
    tasks = []
    transfers = []
    for row in rows:
        lead = row["snapshot"]["lead"]
        unit = row["snapshot"]["unit"]
        text = row["content"]
        markdown += [
            f"## {lead['customer']} · {lead['salesperson']}",
            "",
            text["reason"],
            "",
            f"SMS: {text['sms']}",
            "",
            f"Email: {text['email_subject']}",
            "",
            text["email_body"],
            "",
        ]
        tasks.append(
            [
                lead["lead_id"],
                lead["salesperson"],
                text["email_subject"],
                today,
                "SMS: " + text["sms"] + "\n\nEmail: " + text["email_body"],
            ]
        )
        if unit["transfer"]:
            transfers.append(
                [
                    lead["lead_id"],
                    unit["stock_no"],
                    unit["rooftop_id"],
                    row["rooftop_id"],
                    "Manager review requested; no transfer executed",
                ]
            )
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], token)
        checked_rows(store, conn, job)
        output = dict(
            files={
                "follow-ups.md": "\n".join(markdown),
                "crm-tasks.csv": csv_export(
                    ["lead_id", "salesperson", "task_subject", "due", "message_text"], tasks
                ),
                "transfer-requests.csv": csv_export(
                    ["lead_id", "stock_no", "from_rooftop", "to_rooftop", "status"], transfers
                ),
            },
            count=len(rows),
            rooftop_id=job["payload"]["rooftop_id"],
        )
    return save_result(store, job, token, output)
