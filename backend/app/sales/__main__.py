"""Operator CLI: uv run python -m backend.app.sales run --sample harbor-vale-freight."""

import argparse
import json
import uuid
from pathlib import Path

from ..execution.controller import ROOT
from ..execution.runner import RunError
from ..generation.provider import Budget, ModelConfig, ReplayProvider
from .agent import REPLAYS, live_provider, run_prospect
from .prospects import DEFAULT_OFFERING, Prospects, samples


def main():
    parser = argparse.ArgumentParser(description="Bounded prospect research and unsent draft")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Research one prospect, decide, demonstrate, draft")
    target = run.add_mutually_exclusive_group(required=True)
    target.add_argument("--sample", choices=[s["id"] for s in samples()])
    target.add_argument("--url", help="Public https URL; SSRF policy applies")
    run.add_argument("--offering-file", type=Path, help="Seller offering text (default built in)")
    run.add_argument(
        "--provider",
        choices=["deterministic", "vultr", "replay"],
        default="deterministic",
        help="vultr requires --authorization and VULTR_INFERENCE_API_KEY; replay is free",
    )
    run.add_argument("--authorization", type=Path, help="Exact owner-approved plan JSON")
    sub.add_parser("cleanup", help="Mark abandoned prospect jobs failed; no resend")
    args = parser.parse_args()
    prospects = Prospects(launch=lambda _: None)
    try:
        if args.command == "cleanup":
            prospects.reconcile()
            print(json.dumps({"reconciled": True}))
            return 0
        offering = args.offering_file.read_text() if args.offering_file else DEFAULT_OFFERING
        provider = authorization = None
        mode = "deterministic"
        if args.provider == "vultr":
            if not args.authorization:
                raise RunError("live_authorization_required")
            provider, authorization = live_provider(args.authorization)
            mode = "live_model"
        elif args.provider == "replay":
            provider = ReplayProvider(REPLAYS)
            from ..generation.provider import Authorization

            authorization = Authorization(
                ModelConfig(
                    "qwen3.8-flash-next",
                    deadline_seconds=60,
                    max_input_tokens=16000,
                    max_output_tokens=2048,
                ),
                Budget(max_requests=6, max_total_tokens=131072),
                "saved-replay-no-spend",
                "https://api.vultrinference.com/v1/models",
                "2026-11-05",
            )
            mode = "saved_replay"
        record = prospects.start(
            "cli",
            uuid.uuid4().hex,
            offering=offering,
            url=args.url,
            sample=args.sample,
            mode=mode,
        )
        record = run_prospect(
            prospects,
            record["id"],
            provider=provider,
            authorization=authorization,
        )
        print(
            json.dumps(
                {
                    "status": record["status"],
                    "failure_reason": record["failure_reason"],
                    "mode": record["generation"]["mode"],
                    "sources": [
                        (s["id"], s["status"], s["failure_reason"]) for s in record["sources"]
                    ],
                    "claims": len((record.get("brief") or {}).get("claims", [])),
                    "demo": (record.get("demo") or {}).get("decision"),
                    "demo_status": (record.get("demo") or {}).get("status"),
                    "draft_sha256": (record.get("draft") or {}).get("sha256"),
                    "diagnostics": record["generation"]["diagnostics"],
                    "record": str(prospects.path(record["id"]).relative_to(ROOT)),
                }
            )
        )
        return 0 if record["status"] == "ready" else 1
    except RunError as exc:
        print(json.dumps({"error": exc.reason}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
