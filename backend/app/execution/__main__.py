"""Run with uv run python -m backend.app.execution."""

import argparse
import json
import os
from pathlib import Path

from .artifacts import sha256
from .controller import (
    STORE,
    atomic_json,
    docker_runner,
    execute,
    interruptions,
    recover,
    serial_lock,
)
from .runner import RunError
from .scenarios import FAILURES, PROBES, scenario


def main():
    parser = argparse.ArgumentParser(
        description="Bounded synthetic extraction in local Docker; live inference requires approval"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Execute and verify deterministic extraction fixture")
    probe = sub.add_parser("probe", help="Labelled containment/failure injection; no model calls")
    probe.add_argument("name", choices=["all", *PROBES])
    sub.add_parser("cleanup", help="Recover this checkout's abandoned containers and records")
    generation = sub.add_parser(
        "generate", help="Generate, execute and evaluate one extraction script"
    )
    generation.add_argument("--provider", choices=["fake", "vultr"], required=True)
    generation.add_argument("--model", help="Explicit Vultr model ID; no default live model")
    generation.add_argument(
        "--authorization", type=Path, help="Local exact approved model/budget plan"
    )
    generation.add_argument(
        "--request-controls",
        type=Path,
        help="Separate approved restrictive reasoning controls; one attempt, same budget ledger",
    )
    generation.add_argument(
        "--fake-outcome",
        choices=["success", "correct-once", "fail-twice"],
        default="success",
        help="Offline fault injection only",
    )
    args = parser.parse_args()
    runner = docker_runner()
    try:
        with serial_lock(), interruptions():
            if args.command == "cleanup":
                from ..generation.workflow import recover_workflows

                recovery = recover(runner)
                recovery["reconciled_workflows"] = recover_workflows()
                print(json.dumps(recovery, indent=2))
                return 0
            if args.command == "generate":
                from ..generation.provider import (
                    Authorization,
                    Budget,
                    FakeProvider,
                    ModelConfig,
                    VultrProvider,
                    fake_response,
                    load_request_controls,
                )
                from ..generation.workflow import run_workflow
                from .controller import ROOT

                if args.provider == "fake":
                    if args.authorization or args.model or args.request_controls:
                        raise RunError("fake_provider_configuration_rejected")
                    config = ModelConfig("offline-extraction-fixture")
                    good = (ROOT / "fixtures/evaluation/offline-script.py").read_bytes()
                    bad = (
                        b"from pathlib import Path\nPath('/work/out/result.json').write_text('{}')"
                    )
                    scripts = {
                        "success": [good],
                        "correct-once": [bad, good],
                        "fail-twice": [bad, bad],
                    }[args.fake_outcome]
                    provider = FakeProvider([fake_response(script) for script in scripts])
                    budget = Budget()
                else:
                    if args.fake_outcome != "success":
                        raise RunError("live_fault_injection_rejected")
                    auth = Authorization.load(args.authorization) if args.authorization else None
                    model = args.model or os.environ.get("VULTR_INFERENCE_MODEL")
                    if auth:
                        if model and model != auth.config.model:
                            raise RunError("authorization_model_mismatch")
                        config, budget = auth.config, auth.budget
                    else:
                        config = ModelConfig(model or "")
                        budget = Budget()
                    provider = VultrProvider(auth)
                controls = (
                    load_request_controls(args.request_controls) if args.request_controls else None
                )
                path, record = run_workflow(
                    runner, provider, config, budget, request_controls=controls
                )
                print(
                    json.dumps(
                        {
                            "status": record["status"],
                            "failure_reason": record["failure_reason"],
                            "provider": record["provider"],
                            "attempts": len(record["attempts"]),
                            "budget": record["budget"],
                            "record": str(path),
                        }
                    )
                )
                return (
                    130
                    if record["status"] == "interrupted"
                    else (0 if record["status"] == "succeeded" else 1)
                )
            names = (
                ["fixture"]
                if args.command == "run"
                else ([*PROBES, "fixture"] if args.name == "all" else [args.name])
            )
            passed = True
            for name in names:
                # A new synthetic host file, never a private file. No mount is added.
                canary = STORE / "host-canary.txt"
                canary.write_text("PROOFDESK SYNTHETIC HOST CANARY\n")
                original = sha256(canary.read_bytes())
                task, expected = scenario(name, canary)
                path, record = execute(runner, task, expected, scenario=name)
                expected_failure = FAILURES.get(name)
                check = (
                    record["failure_reason"] == expected_failure
                    and record["status"] == ("failed" if expected_failure else "succeeded")
                    and record["cleanup"]["removed"]
                    and sha256(canary.read_bytes()) == original
                )
                record["probe_check"] = {
                    "expected_failure": expected_failure,
                    "passed": check,
                    "host_canary_before_sha256": original,
                    "host_canary_after_sha256": sha256(canary.read_bytes()),
                }
                atomic_json(path, record)
                passed = passed and check
                print(
                    json.dumps(
                        {
                            "scenario": name,
                            "status": record["status"],
                            "failure_reason": record["failure_reason"],
                            "cleanup": record["cleanup"],
                            "record": str(path),
                            "check_passed": check,
                            "expected_failure": expected_failure,
                        }
                    ),
                    flush=True,
                )
                if record["status"] == "interrupted":
                    return 130
                if not check:
                    return 1
            return 0 if passed else 1
    except RunError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
