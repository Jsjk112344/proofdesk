"""Dealer endpoints retain session capabilities and same-origin write protection."""

import os

from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse

from ..execution.runner import RunError
from .ingestion import MAX_BYTES, parse_csv, template


def register(app, owner, body):
    @app.get("/api/dealer/templates/{kind}.csv")
    def csv_template(kind: str):
        return PlainTextResponse(
            template(kind),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{kind}-template.csv"'},
        )

    @app.post("/api/dealer/import/{kind}")
    async def upload(kind: str, request: Request):
        origin = request.headers.get("origin")
        if (
            request.headers.get("x-proofdesk-request") != "1"
            or (origin and origin != str(request.base_url).rstrip("/"))
            or request.headers.get("sec-fetch-site") == "cross-site"
            or request.headers.get("content-type", "").split(";")[0]
            not in ("text/csv", "application/octet-stream")
        ):
            raise HTTPException(403, "same_origin_csv_required")
        identity = owner(request)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > MAX_BYTES:
                raise HTTPException(413, "csv_file_too_large")
        rows, report = parse_csv(kind, bytes(raw))
        return request.app.state.dealer_store.stage_import(identity, kind, rows, report)

    @app.post("/api/dealer/import")
    async def finish_import(request: Request):
        await body(request, ())
        return request.app.state.dealer_store.finish_import(owner(request))

    @app.get("/api/dealer/data")
    def dealer_data(request: Request):
        identity = owner(request)
        store = request.app.state.dealer_store
        if request.app.state.prospects.public_demo:
            store.seed(identity)
        with store.reading() as conn:
            try:
                group = store.group(conn, identity)
            except RunError:
                return {"imported": False, "validation": []}
        content = group["content"]
        return dict(
            imported=True,
            group=content["group"],
            data_label=content["data_label"],
            validation=content["validation"],
            counts={key: len(content[key]) for key in ("rooftops", "inventory", "leads")},
            floorplan_daily_rate=content["floorplan_daily_rate"],
            match_distance_miles=content["match_distance_miles"],
        )

    @app.post("/api/dealer/sample")
    async def load_sample(request: Request):
        await body(request, ())
        request.app.state.dealer_store.seed(owner(request))
        return {"loaded": True}

    @app.post("/api/dealer/reviews", status_code=202)
    async def review(request: Request):
        data = await body(request, ("request_id",))
        mode = (
            "live_model"
            if (
                request.app.state.prospects.public_demo
                or os.environ.get("SALESDESK_DEALER_LIVE_PLANS")
            )
            else "deterministic"
        )
        request.app.state.dealer_store.seed(owner(request))
        job = request.app.state.dealer_store.start_review(
            owner(request), data["request_id"], mode=mode
        )
        return {"id": job["id"], "status": job["status"]}

    @app.get("/api/dealer")
    def overview(request: Request):
        identity = owner(request)
        store = request.app.state.dealer_store
        store.seed(identity)
        with store.reading() as conn:
            group = store.group(conn, identity)
            parent = store.latest_review(conn, identity)
            jobs = store.jobs(conn, identity)
        children = [j for j in jobs if parent and j["payload"].get("parent_id") == parent["id"]]
        content = group["content"]
        results = {
            j["payload"]["rooftop_id"]: store.result(j)
            for j in children
            if j["status"] == "succeeded"
        }
        childmap = {j["payload"]["rooftop_id"]: j for j in children}
        # Prior accepted sample review is a saved result, never a simulated job.
        # A fresh Run now always creates genuine leased sandbox work.
        baseline = None
        if not parent and content.get("synthetic"):
            import json

            from ..execution.controller import ROOT

            path = ROOT / ".local/dealer-sample-review.json"
            if path.is_file() and path.stat().st_size <= 10 * 1024 * 1024:
                baseline = json.loads(path.read_text())
                if len(baseline.get("results", {})) == 24 and "rollup" in baseline:
                    results = baseline["results"]
                else:
                    baseline = None
        from .handoff import checked_rows, list_followups, materialize

        rooftops = []
        for roof in content["rooftops"]:
            job = childmap.get(roof["id"])
            result = results.get(roof["id"])
            source = (
                job["id"]
                if job
                else (
                    "sample:" + baseline["execution_parent"] + ":" + roof["id"] if baseline else ""
                )
            )
            if result:
                materialize(store, identity, source, result, content)
            with store.reading() as conn:
                cards = list_followups(store, conn, identity, source) if source else []
            cards = [
                {k: row[k] for k in ("id", "lead_id", "content", "version", "sha256", "status")}
                for row in cards
            ]
            rooftops.append(
                dict(
                    **roof,
                    result=result,
                    followups=cards,
                    job={k: job[k] for k in ("id", "status", "events", "failure_reason")}
                    if job
                    else None,
                )
            )
        from .jobs import aggregate

        rollup = (
            store.result(parent)
            if parent and parent["status"] == "succeeded"
            else baseline["rollup"]
            if baseline
            else aggregate(list(results.values()), [])
        )
        handoffs = []
        with store.reading() as conn:
            schedule = conn.execute(
                "SELECT * FROM dealer_schedules WHERE owner=?", (identity,)
            ).fetchone()
            for job in jobs:
                if (
                    job["kind"] != "dealer_handoff"
                    or job["payload"]["group_sha256"] != group["sha256"]
                ):
                    continue
                try:
                    checked_rows(store, conn, job)
                except RunError:
                    continue
                handoffs.append(
                    dict(
                        id=job["id"],
                        rooftop_id=job["payload"]["rooftop_id"],
                        status=job["status"],
                        failure_reason=job["failure_reason"],
                    )
                )
        return dict(
            group=content["group"],
            data_label=content["data_label"],
            rooftops=rooftops,
            review={
                k: parent[k]
                for k in (
                    "id",
                    "status",
                    "events",
                    "created_at",
                    "started_at",
                    "finished_at",
                    "failure_reason",
                )
            }
            if parent
            else None,
            rollup=rollup,
            validation=content["validation"],
            assumptions=dict(
                floorplan_daily_rate=content["floorplan_daily_rate"],
                match_distance_miles=content["match_distance_miles"],
            ),
            concurrency=request.app.state.dealer_scheduler.concurrency,
            handoffs=handoffs,
            schedule=dict(schedule) if schedule else {"enabled": False},
            saved_sample_review=bool(baseline),
        )

    @app.post("/api/dealer/followups/{fid}/edit")
    async def edit_followup(fid: str, request: Request):
        from .handoff import edit

        data = await body(request, ("base_sha256", "content"), limit=8192)
        return edit(
            request.app.state.dealer_store,
            owner(request),
            fid,
            data["base_sha256"],
            data["content"],
        )

    @app.post("/api/dealer/followups/{fid}/skip")
    async def skip_followup(fid: str, request: Request):
        from .handoff import read

        data = await body(request, ("sha256",))
        store = request.app.state.dealer_store
        with store.transaction() as conn:
            saved = read(store, conn, owner(request), fid)
            if saved["sha256"] != data["sha256"]:
                raise RunError("approval_version_conflict")
            conn.execute(
                "UPDATE dealer_followups SET status='skipped',approval=NULL WHERE id=?", (fid,)
            )
        return {"skipped": True}

    @app.post("/api/dealer/stores/{rid}/approve", status_code=202)
    async def approve_store(rid: str, request: Request):
        from .handoff import approve

        data = await body(request, ("versions", "request_id"), limit=256 * 1024)
        job = approve(
            request.app.state.dealer_store,
            owner(request),
            rid,
            data["versions"],
            data["request_id"],
        )
        return {"id": job["id"], "status": job["status"]}

    @app.get("/api/dealer/handoffs/{jid}/{filename}")
    def download_handoff(jid: str, filename: str, request: Request):
        from .handoff import FILES, checked_rows

        if filename not in FILES:
            raise RunError("dealer_not_found")
        store = request.app.state.dealer_store
        with store.reading() as conn:
            job = store.job(conn, jid, owner(request))
            if job["kind"] != "dealer_handoff" or job["status"] != "succeeded":
                raise RunError("dealer_not_found")
            if job["payload"]["group_sha256"] != store.group(conn, owner(request))["sha256"]:
                raise RunError("approval_version_conflict")
            checked_rows(store, conn, job)
        result = store.result(job)
        return PlainTextResponse(
            result["files"][filename],
            media_type="text/csv" if filename.endswith(".csv") else "text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/dealer/schedule")
    async def schedule(request: Request):
        from .schedule import set_schedule

        data = await body(request, ("enabled",))
        return set_schedule(request.app.state.dealer_store, owner(request), data["enabled"])

    @app.post("/api/dealer/assumptions")
    async def assumptions(request: Request):
        import math

        data = await body(request, ("floorplan_daily_rate", "match_distance_miles"))
        for key, maximum in [("floorplan_daily_rate", 1000), ("match_distance_miles", 2000)]:
            if (
                isinstance(data[key], bool)
                or not isinstance(data[key], (int, float))
                or not math.isfinite(data[key])
                or not 0 <= data[key] <= maximum
            ):
                raise RunError("invalid_dealer_assumption")
        store = request.app.state.dealer_store
        with store.reading() as conn:
            group = store.group(conn, owner(request))["content"]
        group.update(data)
        store.save_group(owner(request), group)
        return {"saved": True}
