"""Bootstrap API. Agent execution and external actions are not implemented."""

from fastapi import FastAPI

app = FastAPI(title="SalesDesk", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str | bool]:
    return {
        "service": "proofdesk",
        "status": "scaffold",
        "live_agent": False,
        "containment_verified": False,
    }
