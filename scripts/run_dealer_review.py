"""Operator acceptance: actual parallel Docker review; live mode uses authorized plans."""

import argparse
import json
import time
import uuid
from pathlib import Path

from backend.app.dealer.ingestion import sample_group
from backend.app.dealer.jobs import DealerScheduler
from backend.app.dealer.store import DealerStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default=".local/dealer-acceptance")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    store = DealerStore(Path(args.store).resolve())
    owner = "operator-" + uuid.uuid4().hex
    store.save_group(owner, sample_group())
    parent = store.start_review(
        owner, uuid.uuid4().hex, mode="live_model" if args.live else "deterministic"
    )
    scheduler = DealerScheduler(store)
    scheduler.reconcile(startup=True)
    started = time.monotonic()
    peak = 0
    seen = set()
    scheduler.start()
    try:
        while time.monotonic() - started < 600:
            with store.reading() as conn:
                job = store.job(conn, parent["id"])
                children = [j for j in store.jobs(conn, owner) if j["kind"] == "dealer_rooftop"]
            peak = max(peak, sum(j["status"] == "running" for j in children))
            for child in children:
                if child["status"] in ("succeeded", "failed") and child["id"] not in seen:
                    seen.add(child["id"])
                    print(
                        json.dumps(
                            dict(
                                rooftop=child["payload"]["rooftop_id"],
                                status=child["status"],
                                failure_reason=child["failure_reason"],
                            )
                        ),
                        flush=True,
                    )
            if job["status"] in ("succeeded", "failed"):
                result = store.result(job)
                report = dict(
                    owner=owner,
                    job_id=job["id"],
                    status=job["status"],
                    failure_reason=job["failure_reason"],
                    elapsed_seconds=round(time.monotonic() - started, 3),
                    peak_concurrent_children=peak,
                    result=result,
                )
                (store.root / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
                print(json.dumps({k: v for k, v in report.items() if k != "result"}), flush=True)
                if job["status"] != "succeeded" or (result and result["failures"]):
                    raise SystemExit(1)
                return
            time.sleep(0.25)
        raise SystemExit("acceptance_timeout")
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
