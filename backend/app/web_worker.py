"""Trusted subprocess; source runs only through the existing Docker runner."""

import json
import sys

from .execution.controller import (
    atomic_json,
    docker_runner,
    execute,
    interruptions,
    now,
    serial_lock,
)
from .execution.runner import RunError, Task
from .generation.workflow import cases
from .web_jobs import Jobs, extractor


def work(jobs, run_id, runner=None):
    record = jobs.read(run_id)
    if record["status"] != "queued":
        return  # Recovery/duplicate dispatch never revives terminal work.

    def stage(name):
        with jobs.lock():
            saved = jobs.read(run_id)
            if name != "failed" and saved["status"] == "failed":
                raise RunError(saved["failure_reason"] or "worker_abandoned")
            record["status"] = name
            record["events"].append({"stage": name, "at": now()})
            atomic_json(jobs.path(run_id), record)

    try:
        with serial_lock(jobs.store.parent / "executions"), interruptions():
            stage("preparing")
            script, source = extractor()
            if source != record["extractor"]:
                raise RunError("extractor_changed")
            _, document, answer, _ = next(c for c in cases() if c[0] == record["document_id"])
            runner = runner or docker_runner()
            runner.check_ready()
            stage("executing")
            _, execution = execute(
                runner,
                Task(script, document.read_bytes()),
                json.loads(answer.read_text()),
                scenario="web-" + record["document_id"],
                store=jobs.store.parent / "executions",
                source_kind=source["source_kind"],
                generation=source["generation"],
            )
            record["execution_id"] = execution["id"]
            stage("checking")
            if not execution["cleanup"]["removed"]:
                raise RunError("cleanup_unverified")
            if execution["status"] != "succeeded":
                raise RunError(execution["failure_reason"] or "execution_failed")
            stage("succeeded")
    except KeyboardInterrupt:
        record.update(failure_reason="controller_interrupted")
        stage("failed")
    except RunError as exc:
        record.update(failure_reason=exc.reason)
        stage("failed")
    except Exception:
        record.update(failure_reason="web_worker_internal_error")
        stage("failed")
    finally:
        record["finished_at"] = now()
        with jobs.lock():
            atomic_json(jobs.path(run_id), record)


if __name__ == "__main__":
    work(Jobs(), sys.argv[1])
