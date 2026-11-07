"""Parallel rooftop workers reuse the engine's lease, sandbox and recovery contracts."""

import json
import os
import subprocess
import sys
from pathlib import Path

from ..execution.artifacts import Rejected, sha256, strict_json
from ..execution.controller import (
    ANALYSIS_INPUT_BYTES,
    ANALYSIS_LIMITS,
    ROOT,
    execute,
    recover,
)
from ..execution.runner import DockerRunner, RunError, Task
from ..experiments.jobs import LEASE_SECONDS, Scheduler, _finish, _interrupted
from ..experiments.store import dump
from .matching import expand, reconcile, review_snapshot, typed_input

PROGRAM = Path(__file__).with_name("analysis_program.py")


def runner_for(store, job_id):
    return DockerRunner(
        (ROOT / "infra/task-image.txt").read_text().strip(),
        "dealer-" + sha256(str(store.root.resolve()).encode())[:12] + "-" + job_id,
    )


class DealerScheduler(Scheduler):
    def __init__(self, store, **kwargs):
        super().__init__(
            store,
            concurrency=int(os.environ.get("SALESDESK_DEALER_CONCURRENCY", "6")),
            interval=0.5,
            recover=self.recover_dealer,
            **kwargs,
        )

    def recover_dealer(self):
        # Startup only, before workers are launched. Namespaces are per durable job.
        with self.store.reading() as conn:
            ids = [r[0] for r in conn.execute("SELECT id FROM jobs WHERE kind='dealer_rooftop'")]
        for jid in ids:
            directory = self.store.root / "executions" / jid
            if directory.exists():
                recover(runner_for(self.store, jid), directory)
        return {"reconciled_jobs": len(ids)}

    def tick(self):
        from .schedule import dispatch_due

        dispatch_due(self.store)
        return super().tick()

    def _launch(self, job_id, token):
        allowed = {
            "PATH",
            "HOME",
            "LANG",
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_CONFIG",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
            "PROOFDESK_PUBLIC_DEMO",
            "SALESDESK_DEALER_LIVE_PLANS",
        }
        if os.environ.get("SALESDESK_DEALER_LIVE_PLANS"):
            allowed.add("VULTR_INFERENCE_API_KEY")
        env = {k: v for k, v in os.environ.items() if k in allowed}
        env["SALESDESK_DEALER_STORE"] = str(self.store.root.resolve())
        child = subprocess.Popen(
            [sys.executable, "-m", "backend.app.dealer.worker", job_id, token],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.children[job_id] = (child, token)


def run_job(store, job_id, token, *, runner=None, interpreter=None):
    try:
        with store.transaction() as conn:
            store.verify_lease(conn, job_id, token)
            job = store.job(conn, job_id)
            group = store.group(conn, job["owner"])
            if job["payload"]["group_sha256"] != group["sha256"]:
                raise RunError("dealer_data_changed")
            if job["kind"] == "dealer_rooftop" and job["payload"].get("program_sha256") != sha256(
                PROGRAM.read_bytes()
            ):
                raise RunError("analysis_program_changed")
            store.heartbeat(conn, job, token, LEASE_SECONDS, stage="started")
        if job.get("outcome") and job["outcome"].get("result_path"):
            store.result(job)  # Verify the previously committed artifact hash.
            if job["kind"] == "dealer_handoff":
                from .handoff import checked_rows

                with store.reading() as conn:
                    checked_rows(store, conn, job)
            result = job["outcome"]
        elif job["kind"] == "dealer_rooftop":
            result = rooftop(store, job, token, group["content"], runner, interpreter)
        elif job["kind"] == "dealer_rollup":
            result = rollup(store, job, token, group["content"], interpreter)
        elif job["kind"] == "dealer_handoff":
            from .handoff import prepare

            result = prepare(store, job, token)
        else:
            raise RunError("invalid_job_kind")
        _finish(store, job_id, token, "succeeded", outcome=result)
        if job["kind"] == "dealer_rollup":
            from .schedule import next_due

            with store.transaction() as conn:
                saved = store.job(conn, job_id)
                if saved["status"] == "succeeded":
                    conn.execute(
                        "UPDATE dealer_schedules SET next_due=? WHERE owner=? AND enabled=1",
                        (next_due(), job["owner"]),
                    )
    except KeyboardInterrupt:
        _interrupted(store, job_id, token)
    except (RunError, Rejected) as exc:
        if str(exc) != "job_lease_lost":
            _finish(store, job_id, token, "failed", failure_reason=str(exc))
    except Exception:
        _finish(store, job_id, token, "failed", failure_reason="dealer_worker_internal_error")
    with store.reading() as conn:
        return store.job(conn, job_id)


def heartbeat(store, job, token, stage):
    with store.transaction() as conn:
        store.heartbeat(conn, job, token, LEASE_SECONDS, stage=stage)


def save_result(store, job, token, result):
    with store.transaction() as conn:
        store.verify_lease(conn, job["id"], token)
        path = store.root / "results" / f"{job['id']}.json"
        path.parent.mkdir(exist_ok=True, mode=0o700)
        raw = dump(result).encode()
        # Never overwrite another attempt's accepted final artifact.
        if path.exists() and path.read_bytes() != raw:
            raise RunError("artifact_already_saved")
        path.write_bytes(raw)
        outcome = dict(result_path=str(path.relative_to(store.root)), result_sha256=sha256(raw))
        conn.execute("UPDATE jobs SET outcome=? WHERE id=?", (dump(outcome), job["id"]))
        return outcome


def rooftop(store, job, token, group, runner, interpreter):
    rid = job["payload"]["rooftop_id"]
    if job["payload"].get("review_at"):
        group = review_snapshot(group, job["payload"]["review_at"])
    data = typed_input(group, rid)
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    directory = store.root / "executions" / job["id"]
    heartbeat(store, job, token, "analysing_on_vultr")
    runner = runner or runner_for(store, job["id"])
    runner.check_ready()
    _, record = execute(
        runner,
        Task(PROGRAM.read_bytes(), raw),
        {},
        scenario="dealer-rooftop",
        store=directory,
        limits=ANALYSIS_LIMITS,
        task_bytes=ANALYSIS_INPUT_BYTES,
        validator=lambda value: reconcile(value, data, raw),
        validation="dealer_result_contract_v1",
    )
    if record["status"] != "succeeded" or not record["cleanup"]["removed"]:
        raise RunError(record["failure_reason"] or "cleanup_unverified")
    compact = strict_json((directory / record["id"] / "result.json").read_bytes())
    reconciled = reconcile(compact, data, raw)
    result = expand(compact, data, group)
    result["reconciliation"] = reconciled
    result["execution_id"] = record["id"]
    result["program_sha256"] = sha256(PROGRAM.read_bytes())
    # Prior-night data are separately sandboxed and reconciled, never a host fallback.
    previous = typed_input(group, rid, previous=True)
    prior_parent = job["payload"].get("previous_parent_id")
    prior_metrics = None
    if prior_parent:
        with store.reading() as conn:
            candidates = [
                j
                for j in store.jobs(conn, job["owner"])
                if j["payload"].get("parent_id") == prior_parent
                and j["payload"].get("rooftop_id") == rid
                and j["status"] == "succeeded"
            ]
        if candidates:
            prior_metrics = store.result(candidates[0])["metrics"]
    if prior_metrics is not None:
        result["previous_metrics"] = prior_metrics
    elif previous:
        heartbeat(store, job, token, "comparing_previous_night")
        previous_raw = json.dumps(previous, separators=(",", ":"), sort_keys=True).encode()
        _, prior = execute(
            runner,
            Task(PROGRAM.read_bytes(), previous_raw),
            {},
            scenario="dealer-previous-night",
            store=directory,
            limits=ANALYSIS_LIMITS,
            task_bytes=ANALYSIS_INPUT_BYTES,
            validator=lambda value: reconcile(value, previous, previous_raw),
            validation="dealer_result_contract_v1",
        )
        if prior["status"] != "succeeded":
            raise RunError(prior["failure_reason"] or "previous_night_failed")
        value = strict_json((directory / prior["id"] / "result.json").read_bytes())
        result["previous_metrics"] = value["k"]
    heartbeat(store, job, token, "metrics_validated")
    if interpreter is not None:
        result["brief"] = interpreter("rooftop_brief", result, group, job)
    else:
        from .reasoning import interpret

        result["brief"] = interpret("rooftop_brief", result, group, job, store.root)
    heartbeat(store, job, token, "brief_written")
    return save_result(store, job, token, result)


def aggregate(results, failures):
    failures = list(failures) + [
        dict(rooftop_id=r["rooftop_id"], reason=r["brief"].get("failure_reason", "analyst_failed"))
        for r in results
        if r.get("brief", {}).get("status") == "failed"
    ]
    totals = {
        key: sum(r["metrics"][key] for r in results)
        for key in (
            "open_leads",
            "cold_leads",
            "at_risk",
            "matched_leads",
            "matched_in_stock",
            "aged_60",
            "aged_90",
            "recoverable_gross",
            "floorplan_daily",
            "floorplan_to_date",
        )
    }
    # Sister-store stock can match several rooftops; count distinct aged units at group level.
    totals["aged_matched"] = len(
        {
            m["stock_no"]
            for r in results
            for lead in r["queue"]
            for m in lead["matches"]
            if m["days_on_lot"] >= 60
        }
    )
    source = {}
    for r in results:
        for s in r["sources"]:
            target = source.setdefault(
                s["source"], dict(source=s["source"], total=0, sold=0, appointments=0)
            )
            for key in ("total", "sold", "appointments"):
                target[key] += s[key]
    for s in source.values():
        s["close_rate"] = round(s["sold"] / s["total"], 4) if s["total"] else 0
    previous = {
        key: sum(r.get("previous_metrics", {}).get(key, 0) for r in results)
        for key in totals
        if key != "aged_matched"
    }
    return dict(
        totals=totals,
        failures=failures,
        rooftops=[
            dict(rooftop_id=r["rooftop_id"], **r["metrics"])
            for r in sorted(results, key=lambda r: -r["metrics"]["at_risk"])
        ],
        sources=sorted(source.values(), key=lambda s: -s["close_rate"]),
        deltas={key: round(totals[key] - previous[key], 2) for key in previous}
        if any("previous_metrics" in r for r in results)
        else {},
        gross_definition=(
            "Estimate from listed price minus cost for each at-risk lead best match; "
            "units may repeat; not a sales forecast."
        ),
    )


def rollup(store, job, token, group, interpreter):
    with store.reading() as conn:
        children = [
            j for j in store.jobs(conn, job["owner"]) if j["payload"].get("parent_id") == job["id"]
        ]
    if any(j["status"] in ("running", "scheduled") for j in children):
        raise RunError("dealer_children_pending")
    results = [store.result(j) for j in children if j["status"] == "succeeded"]
    failures = [
        dict(rooftop_id=j["payload"]["rooftop_id"], reason=j["failure_reason"])
        for j in children
        if j["status"] != "succeeded"
    ]
    result = aggregate(results, failures)
    heartbeat(store, job, token, "writing_group_brief")
    if interpreter is not None:
        result["brief"] = interpreter("group_brief", result, group, job)
    else:
        from .reasoning import interpret

        result["brief"] = interpret("group_brief", result, group, job, store.root)
    return save_result(store, job, token, result)
