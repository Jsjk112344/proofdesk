"""Operator live-contract acceptance over already reconciled Docker results.

Retains only accepted model output; failed receipts contain sanitized diagnostics.
Uses durable existing authorization and replay; never resets ledgers.
"""

import argparse
import concurrent.futures
import json
import os
from pathlib import Path

from backend.app.dealer.jobs import aggregate
from backend.app.dealer.reasoning import interpret
from backend.app.dealer.store import DealerStore
from backend.app.execution.controller import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default=".local/dealer-acceptance")
    parser.add_argument("--only")
    args = parser.parse_args()
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("VULTR_INFERENCE_API_KEY="):
            os.environ["VULTR_INFERENCE_API_KEY"] = line.split("=", 1)[1].strip().strip("\"'")
    os.environ["SALESDESK_DEALER_LIVE_PLANS"] = str(ROOT / ".local/dealer-plans")
    store = DealerStore(Path(args.store).resolve())
    acceptance = json.loads((store.root / "acceptance.json").read_text())
    owner = acceptance["owner"]
    with store.reading() as conn:
        group = store.group(conn, owner)["content"]
        jobs = [j for j in store.jobs(conn, owner) if j["kind"] == "dealer_rooftop"]
        parent = store.job(conn, acceptance["job_id"])
    output = ROOT / ".local/dealer-sample-review.json"
    baseline = (
        json.loads(output.read_text())
        if output.exists()
        else dict(
            results={},
            data_label="Sample dealer group",
            reference_time=group["reference_time"],
            execution_parent=parent["id"],
        )
    )

    def process(job):
        rid = job["payload"]["rooftop_id"]
        if args.only and args.only != rid:
            return
        result = store.result(job)
        record = interpret(
            "rooftop_brief",
            result,
            group,
            dict(job, payload=dict(job["payload"], mode="live_model")),
            store.root,
        )
        print(
            json.dumps(
                dict(
                    rooftop=rid,
                    status=record["status"],
                    reason=record.get("failure_reason"),
                    provenance=record["provenance"],
                )
            ),
            flush=True,
        )
        if record["status"] == "succeeded":
            result["brief"] = record
            baseline["results"][rid] = result
        else:
            receipt = max(
                (store.root / "generation" / job["id"]).rglob("generation.json"),
                key=lambda p: p.stat().st_mtime,
            )
            if receipt.exists():
                print(json.dumps(json.loads(receipt.read_text()).get("diagnostic")), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(process, jobs))
    if len(baseline["results"]) == 24 and not args.only:
        rollup = aggregate(list(baseline["results"].values()), [])
        brief = interpret(
            "group_brief",
            rollup,
            group,
            dict(parent, payload=dict(parent["payload"], mode="live_model")),
            store.root,
        )
        print(
            json.dumps(
                dict(
                    group_status=brief["status"],
                    reason=brief.get("failure_reason"),
                    provenance=brief["provenance"],
                )
            ),
            flush=True,
        )
        if brief["status"] == "succeeded":
            rollup["brief"] = brief
            baseline["rollup"] = rollup
        else:
            print(
                json.dumps(
                    json.loads(
                        max(
                            (store.root / "generation" / parent["id"]).rglob("generation.json"),
                            key=lambda p: p.stat().st_mtime,
                        ).read_text()
                    ).get("diagnostic")
                ),
                flush=True,
            )
    output.write_text(json.dumps(baseline, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(accepted_rooftops=len(baseline["results"]), accepted_group="rollup" in baseline)
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
