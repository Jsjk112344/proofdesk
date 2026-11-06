"""Dealer endpoints retain session capabilities and same-origin write protection."""

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
