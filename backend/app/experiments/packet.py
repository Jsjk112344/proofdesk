"""Next-experiment packet: real assembly from approved inputs, with missing data reported.

A packet binds the analysis artifact (by hash), the approved proposal version, the task
and the dataset provenance into one saved JSON document plus a Markdown rendering. It
performs no model call: accepted reasoning is reused with its provenance. Missing
prospective inputs leave the packet at planning review; nothing here launches a campaign,
marks a review complete or claims new sales.
"""

from ..execution.controller import now
from .contracts import format_metric
from .statistics import project_scenario, required_sample_size

PACKET_FORMAT = "salesdesk-experiment-packet-1"


def readiness(proposal, metrics_by_id):
    scenario = proposal["scenario_assumptions"]
    sample = proposal["sample_size_inputs"]
    items = [
        ("audience_size", "Future audience size", scenario["audience_size"]),
        ("gross_margin", "Gross margin (fraction)", scenario["gross_margin"]),
        ("campaign_cost_usd", "Campaign cost (USD)", scenario["campaign_cost_usd"]),
        (
            "minimum_detectable_pp",
            "Minimum detectable effect (pp)",
            sample["minimum_detectable_pp"],
        ),
        ("alpha", "Significance level alpha", sample["alpha"]),
        ("power", "Statistical power", sample["power"]),
    ]
    checks = [
        {
            "input": key,
            "label": label,
            "status": "provided" if value is not None else "missing",
            "value": value,
            "kind": "entered_input",
        }
        for key, label, value in items
    ]
    external = []
    external.append(
        {
            "input": "historical_email_text",
            "label": "Historical e-mail content",
            "status": "unavailable",
            "value": None,
            "note": "Not in the dataset; must not be invented.",
            "kind": "external_prerequisite",
        }
    )
    external.append(
        {
            "input": "consented_eligibility_list",
            "label": "Consented current-customer eligibility list",
            "status": "missing",
            "value": None,
            "note": (
                "Supplied by the owner outside SalesDesk; the historical records are not a list."
            ),
            "kind": "external_prerequisite",
        }
    )
    missing = [c["input"] for c in checks if c["status"] != "provided"]
    return checks + external, missing, external


def assemble_packet(*, task, proposal, run, artifact, manifest, plan, interpretation):
    metrics = run["metrics"]
    by_id = {m["id"]: m for m in metrics}
    checks, missing, external = readiness(proposal["content"], by_id)
    scenario = (
        project_scenario(
            by_id["spend.incremental_per_customer"]["value"],
            by_id["spend.incremental_per_customer"]["interval"] or [None, None],
            proposal["content"]["scenario_assumptions"],
        )
        if by_id["spend.incremental_per_customer"]["interval"]
        else {"available": False, "missing_inputs": ["bootstrap_interval"]}
    )
    sample_inputs = proposal["content"]["sample_size_inputs"]
    sample_size = None
    if all(sample_inputs[k] is not None for k in ("minimum_detectable_pp", "alpha", "power")):
        control_rate = by_id["control.conversion_rate"]["value"]
        if control_rate:
            sample_size = required_sample_size(
                control_rate,
                sample_inputs["minimum_detectable_pp"],
                sample_inputs["alpha"],
                sample_inputs["power"],
            )
    launch_readiness = (
        "inputs_complete_pending_human_launch_decision" if not missing else "planning_review"
    )
    packet = {
        "format": PACKET_FORMAT,
        "generated_at": now(),
        "status": launch_readiness,
        "what_this_is": (
            "A prepared planning packet for a prospective experiment. It is not a launched "
            "campaign, not new responses or sales, and not a completed review."
        ),
        "task": {
            "id": task["id"],
            "title": task["title"],
            "assignee_label": task["assignee_label"],
            "proposed_action": task["proposed_action"],
            "due_date": task["due_date"],
            "approval": task["approval"],
        },
        "bindings": {
            "plan_id": plan["id"],
            "plan_version": plan["version"],
            "plan_sha256": plan["sha256"],
            "run_id": run["id"],
            "analysis_artifact_id": artifact["id"],
            "analysis_artifact_sha256": artifact["sha256"],
            "execution_id": run["execution_id"],
            "program_sha256": run["program_sha256"],
            "proposal_id": proposal["id"],
            "proposal_version": proposal["version"],
            "proposal_sha256": proposal["sha256"],
            "dataset_id": manifest["id"],
            "dataset_raw_sha256": manifest["raw"]["sha256"],
        },
        "source": {
            "title": manifest["source"]["title"],
            "publisher": manifest["source"]["publisher"],
            "description_url": manifest["source"]["description_url"],
            "study_period": manifest["source"]["study_period"],
            "rights": manifest["source"]["rights"],
            "arms": [
                {k: arm[k] for k in ("id", "label", "n", "visits", "conversions", "spend_usd")}
                for arm in manifest["arms"]
            ],
            "limitations": manifest["limitations"],
        },
        "analysis_plan": plan["spec"],
        "historical_result": {
            "metrics": [
                {
                    "id": m["id"],
                    "label": m["label"],
                    "definition": m["definition"],
                    "rendered": format_metric(m),
                    "interval_method": m["interval_method"],
                    "denominator": m["denominator"],
                    "exploratory": m["exploratory"],
                }
                for m in metrics
            ],
            "reconciliation": run["reconciliation"],
        },
        "interpretation": {
            "provenance": interpretation["provenance"] if interpretation else None,
            "label": interpretation["label"] if interpretation else "No interpretation",
            "status": interpretation["status"] if interpretation else "missing",
            "rendered": interpretation.get("rendered") if interpretation else None,
            "note": "Reused as accepted; no model call was made to prepare this packet.",
        },
        "approved_next_experiment": {
            k: proposal["content"][k]
            for k in (
                "hypothesis",
                "variant_a",
                "variant_b",
                "audience_requirements",
                "unit_of_randomization",
                "primary_outcome",
                "observation_window",
                "decision_rule",
                "missing_inputs",
                "notes",
            )
        },
        "scenario": scenario,
        "sample_size": sample_size
        or {
            "available": False,
            "note": "Minimum detectable effect, alpha and power must be entered explicitly; "
            "no default confidence or sample size is substituted.",
        },
        "readiness_checks": checks,
        "unresolved_inputs": missing,
        "external_prerequisites": [c["input"] for c in external],
        "not_claimed": [
            "No campaign was launched and no e-mail was sent.",
            "No new responses or sales were obtained.",
            "The human review task is not completed by preparing this packet.",
            "Historical incremental revenue is not SalesDesk revenue or profit.",
        ],
    }
    return packet


def render_markdown(packet):
    lines = [
        f"# Experiment packet: {packet['task']['title']}",
        "",
        f"Generated {packet['generated_at']} · status `{packet['status']}`",
        "",
        packet["what_this_is"],
        "",
        "## Bindings",
        "",
    ]
    for key, value in packet["bindings"].items():
        lines.append(f"- {key}: `{value}`")
    lines += [
        "",
        "## Source dataset",
        "",
        f"{packet['source']['title']} ({packet['source']['publisher']})",
        "",
    ]
    lines.append("| Arm | Customers | Visits | Purchases | Spend (USD) |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for arm in packet["source"]["arms"]:
        lines.append(
            f"| {arm['label']} | {arm['n']:,} | {arm['visits']:,} | {arm['conversions']:,} "
            f"| {arm['spend_usd']} |"
        )
    lines += ["", "Limitations:", ""] + [f"- {item}" for item in packet["source"]["limitations"]]
    lines += ["", "## Historical result (validated artifact)", ""]
    lines.append("| Metric | Value | Definition |")
    lines.append("| --- | --- | --- |")
    for metric in packet["historical_result"]["metrics"]:
        if metric["exploratory"]:
            continue
        lines.append(f"| {metric['label']} | {metric['rendered']} | {metric['definition']} |")
    exploratory = [m for m in packet["historical_result"]["metrics"] if m["exploratory"]]
    if exploratory:
        lines += ["", "Exploratory breakdowns (descriptive, not confirmatory):", ""]
        for metric in exploratory:
            lines.append(f"- {metric['label']}: {metric['rendered']}")
    interpretation = packet["interpretation"]
    lines += ["", f"## Interpretation ({interpretation['label']})", ""]
    rendered = interpretation.get("rendered")
    if rendered:
        lines += [rendered["question_answered"], "", rendered["interpretation"], ""]
        lines += ["Alternative explanations:", ""] + [
            f"- {a}" for a in rendered["alternative_explanations"]
        ]
        lines += ["", "Unknowns:", ""] + [f"- {u}" for u in rendered["unknowns"]]
    else:
        lines.append(f"No accepted interpretation ({interpretation['status']}).")
    proposal = packet["approved_next_experiment"]
    lines += ["", "## Approved next experiment", "", f"Hypothesis: {proposal['hypothesis']}", ""]
    lines += [f"- Variant A: {proposal['variant_a']}", f"- Variant B: {proposal['variant_b']}"]
    lines += [f"- Unit of randomization: {proposal['unit_of_randomization']}"]
    lines += [f"- Primary outcome: {proposal['primary_outcome']}"]
    lines += [f"- Observation window: {proposal['observation_window']}"]
    lines += [f"- Decision rule: {proposal['decision_rule']}", "", "Audience requirements:", ""]
    lines += [f"- {item}" for item in proposal["audience_requirements"]]
    if proposal["notes"]:
        lines += ["", f"Notes: {proposal['notes']}"]
    lines += ["", "## Scenario (entered assumptions, not measurements)", ""]
    scenario = packet["scenario"]
    if scenario.get("available"):
        lines += [
            f"- Assumptions: audience {scenario['assumptions']['audience_size']:,}, margin "
            f"{scenario['assumptions']['gross_margin']}, campaign cost "
            f"${scenario['assumptions']['campaign_cost_usd']}",
            f"- Projected incremental revenue: ${scenario['projected_incremental_revenue_usd']} "
            f"(interval ${scenario['projected_incremental_revenue_interval_usd'][0]} to "
            f"${scenario['projected_incremental_revenue_interval_usd'][1]})",
            f"- Projected contribution: ${scenario['projected_contribution_usd']} "
            f"(interval ${scenario['projected_contribution_interval_usd'][0]} to "
            f"${scenario['projected_contribution_interval_usd'][1]})",
            f"- {scenario['roi_note']}",
            f"- Transfer assumption: {scenario['transfer_assumption']}",
        ]
    else:
        lines.append(f"Not available; missing inputs: {', '.join(scenario['missing_inputs'])}.")
    lines += ["", "## Sample size", ""]
    sample = packet["sample_size"]
    if sample.get("per_arm"):
        lines.append(
            f"About {sample['per_arm']:,} customers per arm "
            f"({sample['total_two_arms']:,} in total) "
            f"for the entered inputs ({sample['method']}). {sample['note']}"
        )
    else:
        lines.append(sample["note"])
    lines += ["", "## Readiness checks", ""]
    for check in packet["readiness_checks"]:
        value = "" if check["value"] is None else f" = {check['value']}"
        lines.append(f"- {check['label']}: {check['status']}{value}")
    lines += ["", "## Not claimed", ""] + [f"- {item}" for item in packet["not_claimed"]]
    return "\n".join(lines) + "\n"
