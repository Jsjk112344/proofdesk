"""Trusted UI smoke in disposable Docker, with a mocked API and bounded collection.

The mock API replays prospect records produced by the deterministic journey with the
recording runner, so the browser sees realistic shapes without Docker, network or model
calls. This is UI interaction evidence only; it is not execution or inference evidence.
"""

import io
import json
import tarfile
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.app.execution.controller import ROOT, now
from backend.app.execution.runner import command
from backend.app.sales.agent import run_prospect
from backend.app.sales.evidence import SUPPORTED_CAPABILITY
from backend.app.sales.prospects import DEFAULT_OFFERING, MAX_OFFERING, Prospects, samples
from backend.app.web_jobs import checkpoint, documents, extractor
from backend.tests.test_experiments import PLAN
from backend.tests.test_experiments import workspace as experiment_workspace
from backend.tests.test_generation import RecordingRunner


def mock_records():
    """Synthetic journeys for the mocked browser API; labelled UI-MOCK in their ids."""
    with TemporaryDirectory() as temp:
        store = Path(temp) / "prospects"
        prospects = Prospects(store, launch=lambda _: None, live_plan="")
        views = {}
        for sample, runner in (
            ("harbor-vale-freight", RecordingRunner()),
            ("marigold-lane-bakery", RecordingRunner()),
            ("sparse-holding-page", RecordingRunner()),
        ):
            record = prospects.start(
                "ui-mock", uuid.uuid4().hex, offering=DEFAULT_OFFERING, sample=sample
            )
            run_prospect(
                prospects,
                record["id"],
                runner=runner,
                execution_store=Path(temp) / "executions",
            )
            view = prospects.public(prospects.read(record["id"]), "ui-mock")
            if view["execution"]:
                view["execution"]["id"] = "UI-MOCK-EXECUTION"
            views[sample] = view
        failed = json.loads(json.dumps(views["marigold-lane-bakery"]))
        failed.update(
            status="failed",
            failure_reason="research_contract_rejected",
            demo=None,
            draft=None,
            brief=None,
            execution=None,
        )
        failed["prospect"]["display_name"] = "Synthetic live-mode failure"
        failed["prospect"]["kind"] = "public_http"
        failed["prospect"]["input_url"] = "https://prospect.example/"
        failed["generation"] = {
            "mode": "live_model",
            "model": "qwen3.8-flash-next",
            "receipts": {"research": "generation/research/generation.json"},
            "diagnostics": [
                {
                    "contract": "research",
                    "failure_reason": "research_contract_rejected",
                    "diagnostic": {
                        "stage": "contract",
                        "field": "claims[0].excerpt",
                        "expected": "verbatim text from source",
                        "observed": "excerpt_not_in_source",
                        "excerpt_chars": 61,
                    },
                    "finish_reason": "stop",
                    "usage": {
                        "prompt_tokens": 1800,
                        "completion_tokens": 420,
                        "total_tokens": 2220,
                    },
                    "http_status": 200,
                }
            ],
        }
        failed["events"] = failed["events"][:2] + [{"stage": "failed", "at": now()}]
        views["failed"] = failed
        return views


def mock_experiments():
    """Synthetic experiment journey on the labelled fixture dataset, run in-process with the
    test-only host runner; labelled UI-MOCK. Not benchmark evidence."""
    with TemporaryDirectory() as temp:
        root = Path(temp)
        _, service = experiment_workspace(root)
        owner = "ui-mock"
        plan = service.create_plan(owner, uuid.uuid4().hex, PLAN)
        job = service.run_now(plan["id"], owner, uuid.uuid4().hex)
        service.scheduler.tick()
        detail = service.plan_detail(plan["id"], owner)
        proposal = detail["proposals"][0]
        content = dict(proposal["content"])
        content["notes"] = "UI-MOCK edit"
        edited = service.save_proposal(
            plan["id"], owner, uuid.uuid4().hex, content, base_version=proposal["version"]
        )
        task = service.create_task(
            plan["id"],
            owner,
            uuid.uuid4().hex,
            {
                "title": "Review the repeat-experiment packet",
                "assignee_label": "Sales manager",
                "proposed_action": "Review and decide",
                "due_date": "2026-11-12",
            },
        )
        service.approve_task(task["id"], owner, uuid.uuid4().hex, proposal_sha256=edited["sha256"])
        scheduled = service.schedule_task(task["id"], owner, uuid.uuid4().hex, due_at="now")
        service.scheduler.tick()
        final = service.plan_detail(plan["id"], owner)
        packet = service.artifact_view(final["tasks"][0]["packet_artifact_id"], owner)
        service.stop()
        return {
            "kind": "UI-MOCK synthetic fixture journey; not benchmark evidence",
            "overview": service.overview(owner),
            "detail": final,
            "analysis_job": service.job_detail(job["id"], owner),
            "packet_job": service.job_detail(scheduled["job_id"], owner),
            "packet": packet,
        }


def main():
    output = ROOT / ".local/browser"
    output.mkdir(parents=True, exist_ok=True)
    script, source = extractor()
    experiments = mock_experiments()
    workspace = {
        "experiments": {
            "generation_mode": "deterministic",
            "limits": experiments["overview"]["limits"],
            "datasets": [d["id"] for d in experiments["overview"]["datasets"]],
        },
        "capability": SUPPORTED_CAPABILITY,
        "default_offering": DEFAULT_OFFERING,
        "max_offering_chars": MAX_OFFERING,
        "samples": samples(),
        "generation_mode": "deterministic",
        "public_demo": False,
        "inference_checkpoint": checkpoint(),
        "documents": documents(),
        "extractor": source,
        "script": script.decode(),
        "limits": {
            "max_session_prospects": 5,
            "max_total_prospects": 20,
            "max_pages_per_prospect": 4,
        },
    }
    public = {
        **workspace,
        "public_demo": True,
        "limits": {**workspace["limits"], "max_session_prospects": 3, "max_total_prospects": 100},
    }
    data = {
        "workspace.json": json.dumps(workspace).encode(),
        "workspace-public.json": json.dumps(public).encode(),
        "records.json": json.dumps(mock_records()).encode(),
        "experiments.json": json.dumps(experiments).encode(),
        "smoke.mjs": (ROOT / "frontend/tests/smoke.mjs").read_bytes(),
    }
    data.update(
        {
            "dist/" + str(p.relative_to(ROOT / "frontend/dist")): p.read_bytes()
            for p in (ROOT / "frontend/dist").rglob("*")
            if p.is_file()
        }
    )
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, content in data.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(content), 0o644
            archive.addfile(info, io.BytesIO(content))
    name = "proofdesk-ui-" + uuid.uuid4().hex
    try:
        code, _, _ = command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--init",
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                "--ipc=private",
                "--shm-size=256m",
                "--memory=1g",
                "--memory-swap=1g",
                "--cpus=1",
                "--pids-limit=128",
                "--log-driver=none",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=256m,mode=1777",
                "--tmpfs",
                "/work:rw,noexec,nosuid,nodev,size=32m,mode=1777",
                "proofdesk-ui-check",
                "sleep",
                "180",
            ]
        )
        assert code == 0, "browser container unavailable"
        code, _, _ = command(
            ["docker", "exec", "-i", name, "tar", "-xf", "-", "-C", "/work"],
            payload=buffer.getvalue(),
        )
        assert code == 0, "browser input failed"
        code, out, err = command(["docker", "exec", name, "node", "/work/smoke.mjs"], timeout=90)
        (output / "browser.log").write_bytes(out + err)
        assert code == 0, "browser checks failed; inspect ignored browser.log"
        names = {
            "home.png",
            "plan.png",
            "results.png",
            "next-action.png",
            "queue.png",
            "landing.png",
            "research.png",
            "demonstration.png",
            "outreach.png",
            "failure.png",
            "public.png",
            "mobile.png",
            "browser-check.json",
        }
        code, raw, _ = command(
            ["docker", "exec", name, "tar", "-C", "/work", "-cf", "-", *sorted(names)],
            cap=24 * 1024 * 1024,
        )
        assert code == 0, "browser collection failed"
        seen = set()
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            for item in archive:
                assert item.name in names and item.name not in seen
                assert item.isfile() and not item.linkname and not item.issparse()
                assert 0 < item.size <= 4 * 1024 * 1024
                content = archive.extractfile(item).read(4 * 1024 * 1024 + 1)
                assert len(content) == item.size
                if item.name.endswith(".png"):
                    assert content.startswith(b"\x89PNG\r\n\x1a\n")
                (output / item.name).write_bytes(content)
                seen.add(item.name)
        assert seen == names
        print((output / "browser-check.json").read_text())
    finally:
        command(["docker", "rm", "-f", name])
        code, out, _ = command(["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"])
        assert code == 0 and not out.strip(), "browser removal unverified"
        print("Browser container absence verified.")


if __name__ == "__main__":
    main()
