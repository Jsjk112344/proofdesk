"""Prospect journey: research → decision → optional demonstration → draft, with saved progress.

The controller owns every decision. Page text is evidence; a model (when authorized)
proposes a brief or draft through a validated contract and the controller re-derives the
demonstration decision from cited claims. Generated or fixture code runs only in the
existing disposable Docker sandbox. Nothing is sent anywhere.
"""

import json
import os
import time
from pathlib import Path

from ..execution.controller import (
    ROOT,
    STORE,
    atomic_json,
    docker_runner,
    execute,
    interruptions,
    now,
    serial_lock,
)
from ..execution.runner import RunError, Task
from ..generation.provider import Authorization, VultrProvider, complete
from ..generation.workflow import cases
from ..web_jobs import extractor
from .contracts import outreach_contract, research_contract
from .drafting import (
    deterministic_draft,
    draft_hash,
    model_draft,
    outreach_messages,
    research_messages,
)
from .evidence import (
    build_sources,
    classify,
    company_name,
    decide_demo,
    deterministic_brief,
    strip_text,
)
from .retrieval import fetch_site, fixture_site

REPLAYS = ROOT / ".local/replays"
LEDGERS = ROOT / ".local/model-budgets"
REASONING_OFF = {"enabled": False}
JSON_FORMAT = {"type": "json_object"}


def live_provider(plan_path):
    """Operator plan + controller credential; the ledger binds before any request."""
    auth = Authorization.load(Path(plan_path))
    provider = VultrProvider(auth)
    return provider, auth


def run_demo(record, runner, execution_store):
    """Supported capability only: the labelled synthetic extraction in a fresh sandbox."""
    script, source = extractor()
    case, document, answer, _ = cases()[0]
    runner = runner or docker_runner()
    runner.check_ready()
    _, execution = execute(
        runner,
        Task(script, document.read_bytes()),
        json.loads(answer.read_text()),
        scenario="sales-demo-" + case,
        store=execution_store,
        source_kind=source["source_kind"],
        generation=source["generation"],
    )
    demo = record["demo"]
    demo["execution_id"] = execution["id"]
    demo["extractor"] = source
    demo["input_label"] = "Labelled synthetic sample document; not the prospect's data."
    if not execution["cleanup"]["removed"]:
        demo["status"] = "failed"
        demo["failure_reason"] = "cleanup_unverified"
    elif execution["status"] != "succeeded":
        demo["status"] = "failed"
        demo["failure_reason"] = execution["failure_reason"] or "execution_failed"
    else:
        result = json.loads((Path(execution_store) / execution["id"] / "result.json").read_text())
        total = result["total_cents"]
        demo["status"] = "verified"
        demo["failure_reason"] = None
        demo["result_text"] = (
            f"It returned {len(result['items'])} line items and a total of {total} cents "
            f"({result['currency']} {total / 100:.2f}) that matched the expected answer "
            "exactly, and the sandbox was removed afterwards."
        )
    demo["proves"] = (
        "A verified run shows that this extractor produced structured output equal to the "
        "expected answer (compared as canonical JSON values) for a labelled synthetic "
        "document inside an isolated, resource-limited sandbox that was then removed. It "
        "does not show anything about the prospect's documents, volumes or systems."
    )
    return demo


def run_prospect(
    prospects,
    prospect_id,
    *,
    runner=None,
    provider=None,
    authorization=None,
    fetch=fetch_site,
    fixture=fixture_site,
    execution_store=None,
    sandbox_wait=20,
):
    record = prospects.read(prospect_id)
    if record["status"] != "queued":
        return record  # Recovery/duplicate dispatch never revives terminal work.
    directory = prospects.directory(prospect_id)
    execution_store = Path(execution_store or STORE)
    mode = record["generation"]["mode"]

    def stage(name):
        with prospects.lock():
            saved = prospects.read(prospect_id)
            if name != "failed" and saved["status"] == "failed":
                raise RunError(saved["failure_reason"] or "worker_abandoned")
            record["status"] = name
            record["events"].append({"stage": name, "at": now()})
            atomic_json(prospects.path(prospect_id), record)

    def model_step(contract_name, messages, contract):
        nonlocal provider, authorization
        if provider is None:
            plan = os.environ.get("PROOFDESK_SALES_LIVE_PLAN")
            if not plan:
                raise RunError("live_plan_not_configured")
            provider, authorization = live_provider(plan)
        config = authorization.config
        budget = authorization.budget
        if "ledger_id" not in record["generation"]:
            record["generation"]["ledger_id"] = authorization.bind_budget(LEDGERS)
            record["generation"]["model"] = config.model
            record["generation"]["approval_reference"] = authorization.approval_reference
        generation_dir = directory / "generation" / contract_name
        generation_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        receipt_path = generation_dir / "generation.json"
        record["generation"]["receipts"][contract_name] = str(receipt_path.relative_to(directory))
        try:
            value, receipt = complete(
                provider,
                config,
                budget,
                messages,
                receipt_path,
                contract=contract,
                contract_name=contract_name,
                reasoning=REASONING_OFF,
                response_format=JSON_FORMAT,
                replay_store=REPLAYS,
                prefer_replay=os.environ.get("PROOFDESK_PUBLIC_DEMO") == "1",
            )
        except RunError:
            receipt = json.loads(receipt_path.read_text())
            record["generation"]["diagnostics"].append(
                {
                    "contract": contract_name,
                    "failure_reason": receipt["failure_reason"],
                    "diagnostic": receipt.get("diagnostic"),
                    "finish_reason": receipt.get("finish_reason"),
                    "usage": receipt.get("usage"),
                    "http_status": receipt.get("http_status"),
                    "model_echo_matches": receipt.get("model_echo_matches"),
                }
            )
            record["generation"]["budget"] = receipt["budget"]
            record["generation"]["envelope"] = receipt.get("envelope")
            raise
        record["generation"]["budget"] = receipt["budget"]
        record["generation"]["envelope"] = receipt.get("envelope")
        record["generation"]["usage"] = {
            **record["generation"].get("usage", {}),
            contract_name: receipt["usage"],
        }
        value["provenance"] = (
            "saved_replay" if receipt["provider"] == "saved_replay" else "live_model"
        )
        return value

    try:
        with interruptions():
            stage("researching")
            target = record["prospect"]
            pages = fixture(target["sample"]) if target["sample"] else fetch(target["input_url"])
            sources = build_sources(pages)
            (directory / "sources").mkdir(exist_ok=True, mode=0o700)
            for source in sources:
                (directory / "sources" / f"{source['id']}.txt").write_text(source["text"])
            record["sources"] = strip_text(sources)
            atomic_json(prospects.path(prospect_id), record)
            company = company_name(sources, target["input_url"])
            if mode in ("live_model", "saved_replay"):
                brief = model_step(
                    "research",
                    research_messages(record["offering"]["text"], sources, company),
                    lambda content: research_contract(content, sources),
                )
                brief["company_name"] = company
                for claim in brief["claims"]:
                    claim["topic"], claim["strength"] = classify(claim["excerpt"])
                brief["evidence_chars"] = sum(
                    s["text_chars"] for s in sources if s["status"] == "fetched"
                )
                decision = decide_demo(sources, brief["claims"])
                brief["model_demo_relevance"] = brief.pop("demo_relevance")
            else:
                brief, decision = deterministic_brief(sources, target["input_url"])
            record["brief"] = brief
            stage("deciding")
            record["demo"] = {
                **decision,
                "status": "pending" if decision["decision"] == "run" else "skipped",
                "execution_id": None,
                "failure_reason": None,
                "result_text": None,
            }
            atomic_json(prospects.path(prospect_id), record)
            if decision["decision"] == "run":
                stage("demonstrating")
                deadline = time.monotonic() + sandbox_wait
                while True:
                    try:
                        with serial_lock(execution_store):
                            run_demo(record, runner, execution_store)
                        break
                    except RunError as exc:
                        if exc.reason != "another_controller_is_active":
                            raise
                        if time.monotonic() >= deadline:
                            raise RunError("sandbox_busy") from None
                        time.sleep(0.5)
                atomic_json(prospects.path(prospect_id), record)
            stage("drafting")
            if mode in ("live_model", "saved_replay"):
                validated = model_step(
                    "outreach",
                    outreach_messages(record["offering"]["text"], brief, record["demo"], company),
                    lambda content: outreach_contract(
                        content,
                        claims=brief["claims"],
                        offering=record["offering"]["text"],
                        demo=record["demo"],
                    ),
                )
                draft = model_draft(validated, brief, record["demo"], sources)
                if mode == "saved_replay" or validated.get("provenance") == "saved_replay":
                    draft["provenance"] = "saved_replay"
                    brief["provenance"] = "saved_replay"
            else:
                draft = deterministic_draft(
                    record["offering"]["text"], brief, record["demo"], sources
                )
            draft.update(
                version=1,
                sha256=draft_hash(draft["subject"], draft["body"]),
                derived_from=None,
                created_at=now(),
            )
            record["draft"] = draft
            record["review"] = {"state": "pending", "draft_sha256": None, "reviewed_at": None}
            stage("ready")
    except KeyboardInterrupt:
        record.update(failure_reason="controller_interrupted")
        stage("failed")
    except RunError as exc:
        record.update(failure_reason=exc.reason)
        stage("failed")
    except Exception:
        record.update(failure_reason="sales_worker_internal_error")
        stage("failed")
    finally:
        record["finished_at"] = now()
        with prospects.lock():
            atomic_json(prospects.path(prospect_id), record)
    return record
