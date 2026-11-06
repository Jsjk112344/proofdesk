"""Operator CLI for the experiment workspace.

uv run python -m backend.app.experiments import            # verify + import the pinned file
uv run python -m backend.app.experiments fetch             # bounded, checksum-verified download
uv run python -m backend.app.experiments status            # datasets, jobs and tasks summary
uv run python -m backend.app.experiments worker --once     # claim and run due jobs (no API)
"""

import argparse
import json
from pathlib import Path

from ..execution.controller import ROOT
from ..execution.runner import RunError
from .ingestion import HILLSTROM, fetch_dataset, import_dataset
from .jobs import run_job
from .service import Experiments
from .store import Store

DEFAULT_RAW = ROOT / ".local/data-research/hillstrom/hillstrom.csv"


def main():
    parser = argparse.ArgumentParser(description="SalesDesk experiment workspace operations")
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="Verify checksum, validate rows, derive analysis input")
    imp.add_argument("--path", type=Path, default=DEFAULT_RAW)
    fetch = sub.add_parser("fetch", help="Download the pinned source into the ignored cache")
    fetch.add_argument("--destination", type=Path, default=DEFAULT_RAW)
    sub.add_parser("status", help="Summarize datasets, jobs and tasks")
    worker = sub.add_parser("worker", help="Run due jobs from this terminal, one at a time")
    worker.add_argument("--once", action="store_true", help="Process due jobs then exit")
    args = parser.parse_args()
    try:
        store = Store()
        if args.command == "fetch":
            print(json.dumps(fetch_dataset(args.destination)))
            return 0
        if args.command == "import":
            manifest = import_dataset(args.path, HILLSTROM, store.root)
            store.save_dataset(manifest)
            print(
                json.dumps(
                    {
                        "dataset": manifest["id"],
                        "raw_sha256": manifest["raw"]["sha256"],
                        "rows": manifest["raw"]["rows"],
                        "arms": [
                            {k: a[k] for k in ("id", "n", "visits", "conversions", "spend_usd")}
                            for a in manifest["arms"]
                        ],
                        "analysis_input_sha256": manifest["analysis_input"]["sha256"],
                    }
                )
            )
            return 0
        if args.command == "status":
            with store.reading() as conn:
                jobs = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
                tasks = conn.execute(
                    "SELECT status, COUNT(*) FROM tasks GROUP BY status"
                ).fetchall()
                plans = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
            print(
                json.dumps(
                    {
                        "datasets": [d["id"] for d in store.datasets()],
                        "plans": plans,
                        "jobs": {row[0]: row[1] for row in jobs},
                        "tasks": {row[0]: row[1] for row in tasks},
                    }
                )
            )
            return 0
        if args.command == "worker":
            service = Experiments(store, launch=lambda job_id, token: run_job(store, job_id, token))
            processed = []
            while True:
                job = service.scheduler.tick()
                if job is None:
                    break
                processed.append(job["id"])
                if not args.once:
                    continue
            print(json.dumps({"processed": processed}))
            return 0
        return 1
    except RunError as exc:
        print(json.dumps({"error": exc.reason, "detail": getattr(exc, "detail", None)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
