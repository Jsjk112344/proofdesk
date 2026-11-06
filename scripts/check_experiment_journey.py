"""Drive the experiment journey over real HTTP and record evidence (no browser, no mocks).

Covers: dataset overview → saved plan → analysis job run by the server's scheduler in the
Docker sandbox → validated metrics → reproducibility of a second run → proposal edit →
task → version-bound approval → scheduled packet job (the client stops polling until it
is due) → packet download → review completion → cross-session isolation. With
--restart-command it also stops the API while an analysis job is running and verifies
the job is requeued and completed by the restarted process without a duplicate artifact.
"""

import argparse
import http.cookiejar
import json
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from backend.app.execution.controller import ROOT, now

PLAN = {
    "dataset_id": "hillstrom-2008",
    "title": "Mens e-mail versus no e-mail",
    "question": "Did these e-mails create additional purchases, and what should we test next?",
    "comparison": {"treatment": "mens_email", "control": "no_email"},
    "bootstrap": {"seed": 20080320, "resamples": 2000},
    "exploratory_breakdowns": ["newbie", "channel"],
}


class Session:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def call(self, method, path, payload=None, raw=False):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("X-ProofDesk-Request", "1")
        if payload is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with self.opener.open(request, timeout=30) as response:
                body = response.read()
                return response.status, (body if raw else json.loads(body))
        except urllib.error.HTTPError as error:
            body = error.read()
            try:
                return error.code, json.loads(body)
            except ValueError:
                return error.code, body

    def wait_job(self, job_id, timeout=180, interval=1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status, job = self.call("GET", f"/api/experiments/jobs/{job_id}")
            if status == 200 and job["status"] not in ("scheduled", "running"):
                return job
            time.sleep(interval)
        raise SystemExit(f"job {job_id} did not finish")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--restart-command", help="Shell command that restarts the API")
    parser.add_argument(
        "--schedule-delay", type=int, default=20, help="seconds until the packet job"
    )
    args = parser.parse_args()
    evidence = {
        "kind": "real_http_journey",
        "base_url": args.base_url,
        "started_at": now(),
        "steps": [],
    }

    def record(name, **data):
        evidence["steps"].append({"step": name, "at": now(), **data})
        print(json.dumps({"step": name, **{k: v for k, v in data.items() if k != "detail"}})[:400])

    session = Session(args.base_url)
    status, health = session.call("GET", "/api/health")
    record("health", status=status, health=health)
    status, workspace = session.call("GET", "/api/workspace")
    record("workspace", status=status, experiments=workspace["experiments"])
    status, datasets = session.call("GET", "/api/experiments/datasets")
    arms = {
        a["id"]: {k: a[k] for k in ("n", "visits", "conversions", "spend_usd")}
        for a in datasets[0]["arms"]
    }
    record(
        "datasets",
        status=status,
        dataset=datasets[0]["id"],
        raw_sha256=datasets[0]["raw"]["sha256"],
        arms=arms,
    )
    assert arms["mens_email"] == {
        "n": 21307,
        "visits": 3894,
        "conversions": 267,
        "spend_usd": "30311.69",
    }, arms
    assert arms["no_email"] == {
        "n": 21306,
        "visits": 2262,
        "conversions": 122,
        "spend_usd": "13908.33",
    }, arms
    assert arms["womens_email"] == {
        "n": 21387,
        "visits": 3238,
        "conversions": 189,
        "spend_usd": "23038.11",
    }, arms

    status, rejected = session.call(
        "POST",
        "/api/experiments/plans",
        {
            **PLAN,
            "comparison": {"treatment": "new_policy", "control": "no_email"},
            "request_id": uuid4().hex,
        },
    )
    record("plan_rejects_non_original_arm", status=status, detail=rejected.get("detail"))
    assert status == 409 and rejected["detail"] == "invalid_plan_comparison"
    status, plan = session.call(
        "POST", "/api/experiments/plans", {**PLAN, "request_id": uuid4().hex}
    )
    record(
        "plan_saved",
        status=status,
        plan_id=plan["id"],
        version=plan["version"],
        sha256=plan["sha256"],
    )
    assert status == 201

    status, job = session.call(
        "POST", f"/api/experiments/plans/{plan['id']}/runs", {"request_id": uuid4().hex}
    )
    record(
        "run_now_queued",
        status=status,
        job_id=job["id"],
        due_at=job["due_at"],
        mode=job["payload"]["mode"],
    )
    restart = None
    if args.restart_command:
        # Wait until the server's scheduler has claimed the job, then restart the API.
        for _ in range(40):
            _, current = session.call("GET", f"/api/experiments/jobs/{job['id']}")
            if current["status"] == "running":
                break
            time.sleep(0.25)
        restart = {
            "observed_status_before_restart": current["status"],
            "command": args.restart_command,
        }
        subprocess.run(shlex.split(args.restart_command), check=False, timeout=120)
        for _ in range(60):
            try:
                status, _ = session.call("GET", "/api/health")
                if status == 200:
                    break
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            time.sleep(1)
        restart["api_back_at"] = now()
    job = session.wait_job(job["id"])
    record(
        "analysis_job_finished",
        status=job["status"],
        attempts=job["attempts"],
        failure_reason=job["failure_reason"],
        events=[e["stage"] for e in job["events"]],
        outcome=job["outcome"],
        restart=restart,
    )
    assert job["status"] == "succeeded", job
    status, detail = session.call("GET", f"/api/experiments/plans/{plan['id']}")
    run = [r for r in detail["runs"] if r["status"] == "succeeded"][0]
    metrics = {m["id"]: m for m in run["metrics"]}
    summary = {
        key: {"value": metrics[key]["value"], "interval": metrics[key]["interval"]}
        for key in (
            "treatment.conversion_rate",
            "control.conversion_rate",
            "conversion.difference_pp",
            "visit.difference_pp",
            "spend.incremental_per_customer",
        )
    }
    record(
        "analysis_result",
        run_id=run["id"],
        execution_id=run["execution_id"],
        artifact_id=run["artifact_id"],
        program_sha256=run["program_sha256"],
        reconciliation=run["reconciliation"]["status"],
        interpretation={k: run["interpretation"][k] for k in ("status", "provenance", "label")},
        execution={
            k: run["execution"][k]
            for k in ("status", "exit_code", "cleanup", "task_elapsed_seconds", "runtime")
        },
        validation=run["execution"]["validated_artifacts"][0]["validation"],
        metrics=summary,
        runs_total=len(detail["runs"]),
    )
    assert (
        metrics["treatment.purchases"]["value"] == 267
        and metrics["control.purchases"]["value"] == 122
    )
    assert run["execution"]["cleanup"]["removed"] is True
    status, artifact = session.call("GET", f"/api/experiments/artifacts/{run['artifact_id']}")
    first_hash = artifact["sha256"]

    status, job2 = session.call(
        "POST", f"/api/experiments/plans/{plan['id']}/runs", {"request_id": uuid4().hex}
    )
    job2 = session.wait_job(job2["id"])
    status, detail = session.call("GET", f"/api/experiments/plans/{plan['id']}")
    hashes = sorted({r["artifact_id"] for r in detail["runs"] if r["status"] == "succeeded"})
    second = [r for r in detail["runs"] if r["job_id"] == job2["id"]][0]
    status, artifact2 = session.call("GET", f"/api/experiments/artifacts/{second['artifact_id']}")
    record(
        "reproducibility",
        first_sha256=first_hash,
        second_sha256=artifact2["sha256"],
        identical=first_hash == artifact2["sha256"],
        artifacts=hashes,
    )
    assert first_hash == artifact2["sha256"]

    proposal = detail["proposals"][0]
    content = dict(proposal["content"])
    content["scenario_assumptions"] = {
        "audience_size": 50000,
        "gross_margin": 0.4,
        "campaign_cost_usd": "1200.00",
    }
    content["sample_size_inputs"] = {"minimum_detectable_pp": 0.5, "alpha": 0.05, "power": 0.8}
    content["notes"] = "Reviewed by the sales manager during the HTTP journey check."
    status, edited = session.call(
        "POST",
        f"/api/experiments/plans/{plan['id']}/proposal",
        {"proposal": content, "base_version": proposal["version"], "request_id": uuid4().hex},
    )
    record(
        "proposal_edited",
        status=status,
        version=edited["version"],
        provenance=edited["provenance"],
        sha256=edited["sha256"],
    )
    status, task = session.call(
        "POST",
        f"/api/experiments/plans/{plan['id']}/tasks",
        {
            "title": "Review the repeat-experiment packet",
            "assignee_label": "Sales manager",
            "proposed_action": (
                "Review the prepared packet and decide whether to run a repeat with a current "
                "audience."
            ),
            "due_date": (datetime.now(UTC) + timedelta(days=7)).date().isoformat(),
            "request_id": uuid4().hex,
        },
    )
    record("task_created", status=status, task_id=task["id"], task_status=task["status"])
    status, stale = session.call(
        "POST",
        f"/api/experiments/tasks/{task['id']}/approve",
        {"proposal_sha256": proposal["sha256"], "request_id": uuid4().hex},
    )
    record("approval_with_old_version_refused", status=status, detail=stale.get("detail"))
    assert status == 409
    status, approved = session.call(
        "POST",
        f"/api/experiments/tasks/{task['id']}/approve",
        {"proposal_sha256": edited["sha256"], "request_id": uuid4().hex},
    )
    record(
        "task_approved",
        status=status,
        task_status=approved["status"],
        approval=approved["approval"],
    )
    due_at = (datetime.now(UTC) + timedelta(seconds=args.schedule_delay)).isoformat()
    status, scheduled = session.call(
        "POST",
        f"/api/experiments/tasks/{task['id']}/schedule",
        {"due_at": due_at, "request_id": uuid4().hex},
    )
    record(
        "packet_scheduled",
        status=status,
        job_id=scheduled["job_id"],
        due_at=due_at,
        task_status=scheduled["status"],
    )
    # The client goes away: no polling until after the due time.
    time.sleep(args.schedule_delay + 4)
    status, packet_job = session.call("GET", f"/api/experiments/jobs/{scheduled['job_id']}")
    if packet_job["status"] in ("scheduled", "running"):
        packet_job = session.wait_job(scheduled["job_id"])
    record(
        "packet_job_after_client_absence",
        status=packet_job["status"],
        attempts=packet_job["attempts"],
        events=[e["stage"] for e in packet_job["events"]],
        outcome=packet_job["outcome"],
    )
    assert packet_job["status"] == "succeeded", packet_job
    status, detail = session.call("GET", f"/api/experiments/plans/{plan['id']}")
    task = detail["tasks"][0]
    status, markdown = session.call(
        "GET", f"/api/experiments/artifacts/{task['packet_artifact_id']}/packet.md", raw=True
    )
    status2, packet = session.call(
        "GET", f"/api/experiments/artifacts/{task['packet_artifact_id']}"
    )
    body = packet["content"]["packet"]
    record(
        "packet_ready",
        task_status=task["status"],
        packet_artifact_id=task["packet_artifact_id"],
        packet_sha256=packet["sha256"],
        markdown_bytes=len(markdown),
        packet_status=body["status"],
        unresolved_inputs=body["unresolved_inputs"],
        external_prerequisites=body["external_prerequisites"],
        scenario_available=body["scenario"]["available"],
        sample_size_per_arm=body["sample_size"].get("per_arm"),
        model_call=packet_job["outcome"]["model_call"],
    )
    assert task["status"] == "ready_for_review" and markdown.startswith(b"# Experiment packet")
    status, completed = session.call(
        "POST",
        f"/api/experiments/tasks/{task['id']}/complete",
        {
            "evidence_note": (
                "Reviewed the packet during the journey check; audience list still pending."
            ),
            "request_id": uuid4().hex,
        },
    )
    record(
        "task_completed",
        status=status,
        task_status=completed["status"],
        events=[e["stage"] for e in completed["events"]],
    )

    other = Session(args.base_url)
    other.call("GET", "/api/workspace")
    isolation = {
        "plan": other.call("GET", f"/api/experiments/plans/{plan['id']}")[0],
        "job": other.call("GET", f"/api/experiments/jobs/{job['id']}")[0],
        "artifact": other.call("GET", f"/api/experiments/artifacts/{run['artifact_id']}")[0],
        "packet": other.call(
            "GET", f"/api/experiments/artifacts/{task['packet_artifact_id']}/packet.md"
        )[0],
        "overview_plans": len(other.call("GET", "/api/experiments")[1]["plans"]),
    }
    record("cross_session_isolation", **isolation)
    assert isolation == {
        "plan": 404,
        "job": 404,
        "artifact": 404,
        "packet": 404,
        "overview_plans": 0,
    }
    status, overview = session.call("GET", "/api/experiments")
    record(
        "overview",
        plans=len(overview["plans"]),
        tasks=[t["status"] for t in overview["tasks"]],
        jobs=[(j["kind"], j["status"], j["attempts"]) for j in overview["jobs"]],
    )
    evidence["finished_at"] = now()
    evidence["passed"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": True,
                "output": str(args.output.relative_to(ROOT))
                if args.output.is_absolute() and args.output.is_relative_to(ROOT)
                else str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
