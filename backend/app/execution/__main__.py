"""Run with uv run python -m backend.app.execution."""

import argparse
import json

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
        description="Local Docker execution of synthetic fixtures only"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Execute and verify deterministic extraction fixture")
    probe = sub.add_parser("probe", help="Labelled containment/failure injection; no model calls")
    probe.add_argument("name", choices=["all", *PROBES])
    sub.add_parser("cleanup", help="Recover this checkout's abandoned containers and records")
    args = parser.parse_args()
    runner = docker_runner()
    try:
        with serial_lock(), interruptions():
            if args.command == "cleanup":
                print(json.dumps(recover(runner), indent=2))
                return 0
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
            return 0 if passed else 1
    except RunError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
