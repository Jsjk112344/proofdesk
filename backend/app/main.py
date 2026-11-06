"""SalesDesk API: campaign-evaluation experiments plus the supporting prospect workspace.

The experiment workspace opens a pinned historical campaign dataset, saves an analysis
plan, runs the fixed analysis program in the disposable sandbox through a durable job,
shows validated results with an interpretation, and lets a person edit, approve and
schedule a next-experiment packet. The prospect workspace (research, demonstration,
unsent draft) remains a supporting route. No uploads, arbitrary code, sends, raw-dataset
downloads or CRM/mailbox integrations exist over HTTP.
"""

import os
import re
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from .dealer.routes import register as register_dealer
from .dealer.store import DealerStore
from .demo import seed_demo
from .execution.artifacts import sha256, strict_json
from .execution.controller import ROOT
from .execution.runner import RunError
from .experiments.service import Experiments
from .sales.evidence import SUPPORTED_CAPABILITY
from .sales.prospects import DEFAULT_OFFERING, MAX_OFFERING, Prospects, samples
from .web_jobs import Jobs, checkpoint, documents, extractor

COOKIE = "proofdesk_session"
BODY_LIMIT = 16384
NOT_FOUND = {
    "run_not_found",
    "prospect_not_found",
    "execution_not_found",
    "experiment_not_found",
    "dataset_not_found",
    "dealer_not_found",
}
QUOTA = {
    "web_run_quota_reached",
    "prospect_quota_reached",
    "experiment_quota_reached",
    "experiment_queue_full",
    "dealer_quota_reached",
}


def owner(request):
    token = request.cookies.get(COOKIE, "")
    if not re.fullmatch(r"[a-f0-9]{64}", token):
        raise HTTPException(401, "workspace_session_required")
    return sha256(token.encode())


async def body(request, fields, *, limit=2048):
    origin = request.headers.get("origin")
    if (
        request.headers.get("x-proofdesk-request") != "1"
        or (origin and origin != str(request.base_url).rstrip("/"))
        or request.headers.get("sec-fetch-site") == "cross-site"
        or request.headers.get("content-type", "").split(";")[0] != "application/json"
    ):
        raise HTTPException(403, "same_origin_json_required")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > limit:
            raise HTTPException(413, "request_too_large")
    try:
        value = strict_json(bytes(raw))
        if not isinstance(value, dict) or set(value) != set(fields):
            raise ValueError
        return value
    except (ValueError, UnicodeError):
        raise HTTPException(400, "invalid_request") from None


def create_app(jobs=None, prospects=None, experiments=None, dealer_store=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.dealer_store = dealer_store or DealerStore()
        app.state.jobs = jobs or Jobs()
        app.state.prospects = prospects or Prospects()
        app.state.experiments = experiments or Experiments()
        app.state.jobs.reconcile()
        app.state.prospects.reconcile()
        app.state.experiments.reconcile()
        # The API process owns scheduling; the browser only reads and approves.
        app.state.experiments.start()
        yield
        app.state.experiments.stop()
        app.state.jobs.stop()
        app.state.prospects.stop()

    app = FastAPI(title="SalesDesk", version="0.3.0", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=os.environ.get("PROOFDESK_ALLOWED_HOSTS", "127.0.0.1,localhost").split(","),
    )

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                    "base-uri 'none'; form-action 'self'"
                ),
            }
        )
        return response

    @app.exception_handler(RunError)
    async def rejected(request, exc):
        code = 404 if exc.reason in NOT_FOUND else (429 if exc.reason in QUOTA else 409)
        return JSONResponse({"detail": exc.reason}, status_code=code)

    @app.get("/api/health")
    def health(request: Request):
        service = request.app.state.prospects
        experiments = request.app.state.experiments
        return {
            "service": "salesdesk",
            "status": "experiment_workspace",
            "generation_mode": service.mode(),
            "experiments_generation_mode": experiments.mode(),
            "public_demo": service.public_demo,
            "scheduler": "api_process_thread",
        }

    @app.get("/api/workspace")
    def workspace(request: Request, response: Response):
        token = request.cookies.get(COOKIE, "")
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            response.set_cookie(
                COOKIE,
                secrets.token_hex(32),
                httponly=True,
                samesite="strict",
                secure=request.url.scheme == "https",
                path="/api",
                max_age=86400,
            )
        script, source = extractor()
        service = request.app.state.prospects
        experiments = request.app.state.experiments
        return {
            "experiments": {
                "generation_mode": experiments.mode(),
                "limits": experiments.limits,
                "datasets": [d["id"] for d in experiments.datasets()],
            },
            "seeded_demo": experiments.public_demo and service.public_demo,
            "capability": SUPPORTED_CAPABILITY,
            "default_offering": DEFAULT_OFFERING,
            "max_offering_chars": MAX_OFFERING,
            "samples": samples(),
            "generation_mode": service.mode(),
            "public_demo": service.public_demo,
            "inference_checkpoint": checkpoint(),
            "documents": documents(),
            "extractor": source,
            "script": script.decode(),
            "limits": {
                "max_session_prospects": service.max_per_session,
                "max_total_prospects": service.max_total,
                "max_pages_per_prospect": 4,
            },
        }

    @app.post("/api/demo/seed")
    async def seed_public_session(request: Request):
        await body(request, ("request_id",))
        return seed_demo(request.app.state.experiments, request.app.state.prospects, owner(request))

    @app.post("/api/prospects", status_code=202)
    async def start_prospect(request: Request):
        data = await body(
            request, ("offering", "prospect_url", "sample", "request_id"), limit=BODY_LIMIT
        )
        identity = owner(request)
        service = request.app.state.prospects
        service.reconcile()
        url, sample = data["prospect_url"], data["sample"]
        if url is not None and not isinstance(url, str):
            raise RunError("url_host_rejected")
        if sample is not None and not isinstance(sample, str):
            raise RunError("unknown_sample_scenario")
        record = service.start(
            identity,
            data["request_id"],
            offering=data["offering"],
            url=url or None,
            sample=sample or None,
        )
        return service.public(record, identity)

    @app.get("/api/prospects")
    def prospect_history(request: Request):
        service = request.app.state.prospects
        service.reconcile()
        identity = owner(request)
        return [service.public(r, identity) for r in service.records() if r["owner"] == identity]

    @app.get("/api/prospects/{prospect_id}")
    def prospect_detail(prospect_id: str, request: Request):
        service = request.app.state.prospects
        service.reconcile()
        return service.public(service.read(prospect_id), owner(request))

    @app.post("/api/prospects/{prospect_id}/draft")
    async def edit_draft(prospect_id: str, request: Request):
        data = await body(
            request, ("subject", "body", "base_sha256", "request_id"), limit=BODY_LIMIT
        )
        identity = owner(request)
        service = request.app.state.prospects
        record = service.edit_draft(
            prospect_id,
            identity,
            data["request_id"],
            subject=data["subject"],
            body=data["body"],
            base_sha256=data["base_sha256"],
        )
        return service.public(record, identity)

    @app.post("/api/prospects/{prospect_id}/review")
    async def review_draft(prospect_id: str, request: Request):
        data = await body(request, ("draft_sha256",))
        identity = owner(request)
        service = request.app.state.prospects
        record = service.review(prospect_id, identity, draft_sha256=data["draft_sha256"])
        return service.public(record, identity)

    # Experiment workspace: datasets are aggregate-only; everything else is owner-scoped.
    @app.get("/api/experiments")
    def experiments_overview(request: Request):
        return request.app.state.experiments.overview(owner(request))

    @app.get("/api/experiments/datasets")
    def experiment_datasets(request: Request):
        return request.app.state.experiments.datasets()

    @app.get("/api/experiments/datasets/{dataset_id}")
    def experiment_dataset(dataset_id: str, request: Request):
        return request.app.state.experiments.dataset(dataset_id)

    @app.post("/api/experiments/plans", status_code=201)
    async def create_plan(request: Request):
        data = await body(
            request,
            (
                "dataset_id",
                "title",
                "question",
                "comparison",
                "bootstrap",
                "exploratory_breakdowns",
                "request_id",
            ),
            limit=BODY_LIMIT,
        )
        identity = owner(request)
        request_id = data.pop("request_id")
        return request.app.state.experiments.create_plan(identity, request_id, data)

    @app.get("/api/experiments/plans/{plan_id}")
    def plan_detail(plan_id: str, request: Request):
        return request.app.state.experiments.plan_detail(plan_id, owner(request))

    @app.post("/api/experiments/plans/{plan_id}/runs", status_code=202)
    async def run_plan(plan_id: str, request: Request):
        data = await body(request, ("request_id",))
        return request.app.state.experiments.run_now(plan_id, owner(request), data["request_id"])

    @app.post("/api/experiments/plans/{plan_id}/proposal", status_code=201)
    async def save_proposal(plan_id: str, request: Request):
        data = await body(request, ("proposal", "base_version", "request_id"), limit=BODY_LIMIT)
        return request.app.state.experiments.save_proposal(
            plan_id,
            owner(request),
            data["request_id"],
            data["proposal"],
            base_version=data["base_version"],
        )

    @app.post("/api/experiments/plans/{plan_id}/tasks", status_code=201)
    async def create_task(plan_id: str, request: Request):
        data = await body(
            request,
            ("title", "assignee_label", "proposed_action", "due_date", "request_id"),
            limit=BODY_LIMIT,
        )
        request_id = data.pop("request_id")
        return request.app.state.experiments.create_task(plan_id, owner(request), request_id, data)

    @app.post("/api/experiments/tasks/{task_id}/approve")
    async def approve_task(task_id: str, request: Request):
        data = await body(request, ("proposal_sha256", "request_id"))
        return request.app.state.experiments.approve_task(
            task_id, owner(request), data["request_id"], proposal_sha256=data["proposal_sha256"]
        )

    @app.post("/api/experiments/tasks/{task_id}/schedule", status_code=202)
    async def schedule_task(task_id: str, request: Request):
        data = await body(request, ("due_at", "request_id"))
        return request.app.state.experiments.schedule_task(
            task_id, owner(request), data["request_id"], due_at=data["due_at"]
        )

    @app.post("/api/experiments/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str, request: Request):
        await body(request, ())
        return request.app.state.experiments.cancel_task(task_id, owner(request))

    @app.post("/api/experiments/tasks/{task_id}/complete")
    async def complete_task(task_id: str, request: Request):
        data = await body(request, ("evidence_note", "request_id"), limit=BODY_LIMIT)
        return request.app.state.experiments.complete_task(
            task_id, owner(request), data["request_id"], evidence_note=data["evidence_note"]
        )

    @app.get("/api/experiments/jobs/{job_id}")
    def job_detail(job_id: str, request: Request):
        return request.app.state.experiments.job_detail(job_id, owner(request))

    @app.post("/api/experiments/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str, request: Request):
        await body(request, ())
        return request.app.state.experiments.cancel_job(job_id, owner(request))

    @app.get("/api/experiments/artifacts/{artifact_id}")
    def artifact_detail(artifact_id: str, request: Request):
        return request.app.state.experiments.artifact_view(artifact_id, owner(request))

    @app.get("/api/experiments/artifacts/{artifact_id}/packet.md")
    def packet_download(artifact_id: str, request: Request):
        markdown, artifact = request.app.state.experiments.packet_markdown(
            artifact_id, owner(request)
        )
        filename = f"experiment-packet-{artifact_id[:8]}.md"
        return PlainTextResponse(
            markdown,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # The extraction endpoints remain for the demonstration capability and existing
    # records; they are no longer the product's entry point.
    @app.post("/api/runs", status_code=202)
    async def start(request: Request):
        data = await body(request, ("document_id", "request_id"))
        identity = owner(request)
        service = request.app.state.jobs
        service.reconcile()
        return service.public(
            service.start(data["document_id"], identity, data["request_id"]), identity
        )

    @app.get("/api/runs")
    def history(request: Request):
        service = request.app.state.jobs
        service.reconcile()
        identity = owner(request)
        return [service.public(r, identity) for r in service.records() if r["owner"] == identity]

    @app.get("/api/runs/{run_id}")
    def detail(run_id: str, request: Request):
        service = request.app.state.jobs
        service.reconcile()
        return service.public(service.read(run_id), owner(request))

    register_dealer(app, owner, body)

    dist = ROOT / "frontend/dist"
    if dist.is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app


app = create_app()
