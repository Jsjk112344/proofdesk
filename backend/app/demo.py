"""Idempotent public examples through the normal owner-scoped operations and workers.

This prepares a labelled example approval authorized for the demo, never an outreach send
or a visitor's approval of newly edited content. All normal quotas still count.
"""

from .execution.artifacts import sha256
from .execution.runner import RunError
from .sales.prospects import DEFAULT_OFFERING

BENCHMARK_PLAN = {
    "dataset_id": "hillstrom-2008",
    "title": "Mens e-mail versus no e-mail",
    "question": "Did these e-mails create additional purchases, and what should we test next?",
    "comparison": {"treatment": "mens_email", "control": "no_email"},
    "bootstrap": {"seed": 20080320, "resamples": 2000},
    "exploratory_breakdowns": ["newbie", "channel"],
}


def seed_demo(experiments, prospects, owner):
    if not experiments.public_demo or not prospects.public_demo:
        raise RunError("experiment_not_found")
    plan = experiments.create_plan(owner, sha256(b"demo-seed-plan")[0:32], BENCHMARK_PLAN)
    job = experiments.run_now(plan["id"], owner, sha256(b"demo-seed-analysis")[0:32])
    try:
        prospect = prospects.start(
            owner,
            sha256(b"demo-seed-prospect")[0:32],
            offering=DEFAULT_OFFERING,
            sample="harbor-vale-freight",
        )
    except RunError as exc:
        if exc.reason != "another_prospect_is_active":
            raise
        return {"plan_id": plan["id"], "ready": False, "stage": "Waiting for a Vultr worker"}
    result = {"plan_id": plan["id"], "prospect_id": prospect["id"], "ready": False}
    job = experiments.job_detail(job["id"], owner)
    if job["status"] == "failed":
        raise RunError(job["failure_reason"] or "demo_analysis_failed")
    if prospect["status"] == "failed":
        raise RunError(prospect["failure_reason"] or "demo_prospect_failed")
    if job["status"] != "succeeded":
        return {**result, "stage": "Analysing the benchmark on Vultr"}
    detail = experiments.plan_detail(plan["id"], owner)
    if not detail["proposals"]:
        raise RunError("demo_interpretation_failed")
    task = experiments.create_task(
        plan["id"],
        owner,
        sha256(b"demo-seed-task")[0:32],
        {
            "title": "Demo example: review the next-move packet",
            "assignee_label": "Demo sales manager",
            "proposed_action": "Review this seeded example packet before any campaign decision.",
            "due_date": None,
        },
    )
    # Never re-approve a changed example or revive visitor-cancelled work on reload.
    if task["status"] in ("cancelled", "completed"):
        return {**result, "ready": True, "stage": "Example already initialized"}
    proposal = detail["proposals"][0]
    if task["proposal_sha256"] != proposal["sha256"]:
        return {**result, "ready": True, "stage": "Example edited by visitor"}
    if task["status"] == "pending_review":
        task = experiments.approve_task(
            task["id"],
            owner,
            sha256(b"demo-seed-approval")[0:32],
            proposal_sha256=proposal["sha256"],
        )
    if task["status"] == "approved":
        task = experiments.schedule_task(
            task["id"], owner, sha256(b"demo-seed-packet")[0:32], due_at="now"
        )
    if task["status"] == "failed":
        raise RunError("demo_packet_failed")
    return {
        **result,
        "ready": task["status"] == "ready_for_review" and prospect["status"] == "ready",
        "stage": "Preparing your example packet and prospect brief on Vultr",
    }
