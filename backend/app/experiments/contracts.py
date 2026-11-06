"""Validated contracts for plans, sandbox results, metrics, model reasoning and states.

Deterministic code owns every number shown to a person: metrics are derived from the
validated analysis artifact, reconciled against the importer's independent aggregates and
the controller's own interval implementation. A model (when authorized) may only refer to
metrics by id through `[metric:ID]` placeholders; prose digits, percentages, currency,
ROI/profit wording and instructions to contact the historical records are refused. These
are lexical checks against validated values, not proof that an interpretation is right.
"""

import json
import math
import re

from ..execution.artifacts import Rejected, sha256
from ..execution.runner import RunError
from ..sales.contracts import ContractError, diagnostic, json_object, observed_type
from ..sales.evidence import normalize
from .analysis_program import PROGRAM_VERSION, RESULT_FORMAT
from .statistics import (
    CONFIDENCE_LEVEL,
    newcombe_difference,
    relative_change,
    wilson_interval,
)

PRIMARY_OUTCOME = "conversion"
SECONDARY_OUTCOMES = ["visit", "spend"]
RESAMPLE_CHOICES = (1000, 2000, 4000)
BREAKDOWNS = ("newbie", "channel")
MAX_SEED = 2**31 - 1
MAX_LIST = 10
TOLERANCE = 1e-9
PLACEHOLDER = re.compile(r"\[metric:([a-z0-9_.]{1,80})\]")
_DIGIT_OR_SYMBOL = re.compile(r"[0-9%$€£]")
_ROI_WORDS = re.compile(
    r"\b(roi|profits?|profitable|payback|guarantee[sd]?|realized|realised|proven|"
    r"will (?:increase|lift|grow|boost)|increased sales|more sales)\b",
    re.IGNORECASE,
)
_CONTACT_VERBS = re.compile(
    r"\b(contact|e-?mail|re-?e-?mail|message|call|send|target|re-?target|mail|reach out to)\b",
    re.IGNORECASE,
)
_HISTORICAL_RECORDS = re.compile(
    r"\b(these|those|the same|historical|original|the dataset'?s?|the benchmark'?s?|2008)\s+"
    r"(customers?|records?|recipients?|people|contacts?|rows?|individuals?|households?)\b",
    re.IGNORECASE,
)
TASK_STATES = frozenset(
    {
        "pending_review",
        "approved",
        "scheduled",
        "running",
        "ready_for_review",
        "completed",
        "cancelled",
        "failed",
    }
)
TASK_TRANSITIONS = {
    "pending_review": {"approved", "cancelled"},
    "approved": {"scheduled", "pending_review", "cancelled"},
    "scheduled": {"running", "failed", "pending_review", "cancelled"},
    "running": {"ready_for_review", "failed", "cancelled"},
    "ready_for_review": {"completed", "cancelled"},
    "failed": {"scheduled", "pending_review", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
JOB_STATES = frozenset({"scheduled", "running", "succeeded", "failed", "cancelled"})
JOB_TRANSITIONS = {
    "scheduled": {"running", "cancelled"},
    "running": {"succeeded", "failed", "scheduled", "cancelled"},
    "succeeded": set(),
    "failed": set(),
    "cancelled": set(),
}
JOB_KINDS = frozenset(
    {"analyze_plan", "prepare_packet", "dealer_rooftop", "dealer_rollup", "dealer_handoff"}
)


def transition(kind, current, target):
    table = TASK_TRANSITIONS if kind == "task" else JOB_TRANSITIONS
    if target not in table.get(current, set()):
        raise RunError(f"invalid_{kind}_transition")
    return target


def _text(value, field, *, minimum=1, maximum=400, allow_empty=False):
    if not isinstance(value, str) or "\x00" in value:
        raise RunError(f"invalid_{field}")
    value = normalize(value)
    if allow_empty and not value:
        return ""
    if not minimum <= len(value) <= maximum:
        raise RunError(f"invalid_{field}")
    return value


def _text_list(value, field, *, maximum_items=MAX_LIST, maximum=240, minimum_items=0):
    if not isinstance(value, list) or not minimum_items <= len(value) <= maximum_items:
        raise RunError(f"invalid_{field}")
    return [_text(item, field, maximum=maximum) for item in value]


def validate_plan_spec(data, manifest):
    """Canonical plan specification from a request body and the dataset manifest."""
    if not isinstance(data, dict):
        raise RunError("invalid_plan")
    allowed = {"title", "question", "comparison", "bootstrap", "exploratory_breakdowns"}
    if set(data) != allowed:
        raise RunError("invalid_plan")
    arms = {arm["id"] for arm in manifest["arms"]}
    comparison = data["comparison"]
    if (
        not isinstance(comparison, dict)
        or set(comparison) != {"treatment", "control"}
        or comparison["treatment"] not in arms
        or comparison["control"] not in arms
        or comparison["treatment"] == comparison["control"]
    ):
        raise RunError("invalid_plan_comparison")
    bootstrap = data["bootstrap"]
    if (
        not isinstance(bootstrap, dict)
        or set(bootstrap) != {"seed", "resamples"}
        or type(bootstrap["seed"]) is not int
        or not 0 <= bootstrap["seed"] <= MAX_SEED
        or bootstrap["resamples"] not in RESAMPLE_CHOICES
    ):
        raise RunError("invalid_plan_bootstrap")
    breakdowns = data["exploratory_breakdowns"]
    if (
        not isinstance(breakdowns, list)
        or len(set(breakdowns)) != len(breakdowns)
        or any(b not in BREAKDOWNS for b in breakdowns)
    ):
        raise RunError("invalid_plan_breakdowns")
    return {
        "title": _text(data["title"], "plan_title", maximum=120),
        "question": _text(data["question"], "plan_question", maximum=300),
        "dataset_id": manifest["id"],
        "dataset_raw_sha256": manifest["raw"]["sha256"],
        "comparison": {"treatment": comparison["treatment"], "control": comparison["control"]},
        "primary_outcome": PRIMARY_OUTCOME,
        "secondary_outcomes": list(SECONDARY_OUTCOMES),
        "confidence_level": CONFIDENCE_LEVEL,
        "bootstrap": {"seed": bootstrap["seed"], "resamples": bootstrap["resamples"]},
        "exploratory_breakdowns": [b for b in BREAKDOWNS if b in breakdowns],
        "retrospective": True,
        "preregistered": False,
    }


def plan_line(spec):
    """The exact JSON line the sandbox receives; its hash binds the artifact to the plan."""
    keys = (
        "comparison",
        "primary_outcome",
        "secondary_outcomes",
        "confidence_level",
        "bootstrap",
        "exploratory_breakdowns",
    )
    return json.dumps({k: spec[k] for k in keys}, sort_keys=True)


def plan_hash(spec):
    return sha256(plan_line(spec).encode())


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _close(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= TOLERANCE * max(1.0, abs(a), abs(b))


def _interval_close(a, b):
    if a is None and b is None:
        return True
    return (
        isinstance(a, list)
        and isinstance(b, (list, tuple))
        and len(a) == 2
        and _close(a[0], b[0])
        and _close(a[1], b[1])
    )


def _check(condition, reason):
    if not condition:
        raise Rejected(reason)


def validate_result(parsed, *, manifest, spec, input_sha256, program_sha256):
    """Analysis-result contract plus reconciliation with independent host computations."""
    _check(isinstance(parsed, dict), "analysis_result_not_object")
    expected_keys = {
        "format",
        "program_version",
        "dataset_id",
        "dataset_raw_sha256",
        "analysis_input_sha256",
        "plan_sha256",
        "rows_read",
        "arms",
        "comparison",
        "exploratory",
    }
    _check(set(parsed) == expected_keys, "analysis_result_keys_mismatch")
    _check(parsed["format"] == RESULT_FORMAT, "analysis_result_format_mismatch")
    _check(parsed["program_version"] == PROGRAM_VERSION, "analysis_program_version_mismatch")
    _check(parsed["dataset_id"] == manifest["id"], "analysis_dataset_mismatch")
    _check(
        parsed["dataset_raw_sha256"] == manifest["raw"]["sha256"], "analysis_dataset_hash_mismatch"
    )
    _check(parsed["analysis_input_sha256"] == input_sha256, "analysis_input_hash_mismatch")
    _check(parsed["plan_sha256"] == plan_hash(spec), "analysis_plan_hash_mismatch")
    _check(parsed["rows_read"] == manifest["raw"]["rows"], "analysis_row_count_mismatch")
    checks = []
    arms = parsed["arms"]
    manifest_arms = {arm["id"]: arm for arm in manifest["arms"]}
    _check(isinstance(arms, dict) and set(arms) == set(manifest_arms), "analysis_arms_mismatch")
    for arm_id, counts in arms.items():
        expected = manifest_arms[arm_id]
        _check(
            isinstance(counts, dict)
            and set(counts) == {"n", "visits", "conversions", "spend_cents", "buyers"}
            and all(type(counts[k]) is int for k in counts),
            "analysis_arm_counts_malformed",
        )
        for key in ("n", "visits", "conversions", "spend_cents", "buyers"):
            _check(counts[key] == expected[key], f"reconciliation_mismatch_{key}")
        checks.append({"arm": arm_id, "counts_and_spend_cents": "matched_importer_aggregates"})
    comparison = parsed["comparison"]
    _check(isinstance(comparison, dict), "analysis_comparison_malformed")
    _check(
        comparison.get("treatment") == spec["comparison"]["treatment"]
        and comparison.get("control") == spec["comparison"]["control"],
        "analysis_comparison_arms_mismatch",
    )
    treatment, control = arms[comparison["treatment"]], arms[comparison["control"]]
    for outcome, key in (("conversion", "conversions"), ("visit", "visits")):
        section = comparison.get(outcome)
        _check(isinstance(section, dict), f"analysis_{outcome}_malformed")
        for role, counts in (("treatment", treatment), ("control", control)):
            part = section.get(role)
            _check(
                isinstance(part, dict)
                and part.get("events") == counts[key]
                and part.get("n") == counts["n"],
                f"analysis_{outcome}_{role}_counts_mismatch",
            )
            expected_rate = counts[key] / counts["n"] if counts["n"] else None
            _check(
                _close(part.get("rate"), expected_rate), f"analysis_{outcome}_{role}_rate_mismatch"
            )
            _check(
                _interval_close(part.get("interval"), wilson_interval(counts[key], counts["n"])),
                f"analysis_{outcome}_{role}_interval_mismatch",
            )
        difference = newcombe_difference(treatment[key], treatment["n"], control[key], control["n"])
        rate_t = treatment[key] / treatment["n"] if treatment["n"] else None
        rate_c = control[key] / control["n"] if control["n"] else None
        expected_difference = rate_t - rate_c if rate_t is not None and rate_c is not None else None
        _check(
            _close(section.get("difference"), expected_difference),
            f"analysis_{outcome}_difference_mismatch",
        )
        _check(
            _interval_close(section.get("difference_interval"), difference),
            f"analysis_{outcome}_difference_interval_mismatch",
        )
        _check(
            _close(section.get("relative_change"), relative_change(rate_t, rate_c)),
            f"analysis_{outcome}_relative_change_mismatch",
        )
        checks.append(
            {"outcome": outcome, "wilson_and_newcombe": "matched_controller_implementation"}
        )
    spend = comparison.get("spend")
    _check(isinstance(spend, dict), "analysis_spend_malformed")
    for role, counts in (("treatment", treatment), ("control", control)):
        part = spend.get(role)
        _check(
            isinstance(part, dict)
            and part.get("n") == counts["n"]
            and part.get("total_cents") == counts["spend_cents"],
            f"analysis_spend_{role}_counts_mismatch",
        )
        expected_mean = counts["spend_cents"] / counts["n"] if counts["n"] else None
        _check(
            _close(part.get("mean_cents"), expected_mean), f"analysis_spend_{role}_mean_mismatch"
        )
    mean_t = treatment["spend_cents"] / treatment["n"] if treatment["n"] else None
    mean_c = control["spend_cents"] / control["n"] if control["n"] else None
    expected_difference = mean_t - mean_c if mean_t is not None and mean_c is not None else None
    _check(
        _close(spend.get("difference_cents"), expected_difference),
        "analysis_spend_difference_mismatch",
    )
    bootstrap = spend.get("bootstrap")
    if treatment["n"] and control["n"]:
        _check(
            isinstance(bootstrap, dict)
            and bootstrap.get("seed") == spec["bootstrap"]["seed"]
            and bootstrap.get("resamples") == spec["bootstrap"]["resamples"]
            and isinstance(bootstrap.get("interval_cents"), list)
            and len(bootstrap["interval_cents"]) == 2
            and all(_finite(v) for v in bootstrap["interval_cents"])
            and bootstrap["interval_cents"][0] <= bootstrap["interval_cents"][1]
            and _finite(bootstrap.get("se_cents"))
            and bootstrap["se_cents"] >= 0
            and re.fullmatch(r"[0-9a-f]{64}", str(bootstrap.get("replicates_sha256"))),
            "analysis_bootstrap_malformed",
        )
        checks.append({"spend": "bootstrap_seed_and_resamples_match_plan"})
    else:
        _check(bootstrap is None, "analysis_bootstrap_unexpected")
        checks.append({"spend": "bootstrap_skipped_empty_group"})
    exploratory = parsed["exploratory"]
    _check(
        isinstance(exploratory, dict)
        and exploratory.get("label") == "exploratory_descriptive_only"
        and isinstance(exploratory.get("breakdowns"), dict)
        and set(exploratory["breakdowns"]) == set(spec["exploratory_breakdowns"]),
        "analysis_exploratory_mismatch",
    )
    for breakdown, cells in exploratory["breakdowns"].items():
        _check(isinstance(cells, dict) and len(cells) <= 12, "analysis_exploratory_malformed")
        totals = {"treatment": 0, "control": 0}
        for level, cell in cells.items():
            _check(isinstance(level, str) and len(level) <= 20, "analysis_exploratory_malformed")
            for role in ("treatment", "control"):
                part = cell.get(role) if isinstance(cell, dict) else None
                _check(
                    isinstance(part, dict)
                    and type(part.get("n")) is int
                    and type(part.get("conversions")) is int
                    and 0 <= part["conversions"] <= part["n"]
                    and _close(
                        part.get("rate"), part["conversions"] / part["n"] if part["n"] else None
                    ),
                    "analysis_exploratory_malformed",
                )
                totals[role] += part["n"]
        _check(
            totals["treatment"] == treatment["n"] and totals["control"] == control["n"],
            "analysis_exploratory_totals_mismatch",
        )
    checks.append({"hashes": "dataset, analysis input, plan and program bound"})
    return {
        "status": "matched",
        "program_sha256": program_sha256,
        "independent_implementation": "importer Decimal aggregates; controller Wilson/Newcombe",
        "checks": checks,
    }


def _metric(
    metric_id,
    label,
    definition,
    kind,
    value,
    *,
    unit=None,
    interval=None,
    interval_method=None,
    denominator=None,
    path=None,
    exploratory=False,
):
    return {
        "id": metric_id,
        "label": label,
        "definition": definition,
        "kind": kind,
        "value": value,
        "unit": unit,
        "interval": interval,
        "interval_method": interval_method,
        "level": CONFIDENCE_LEVEL if interval is not None else None,
        "denominator": denominator,
        "path": path,
        "exploratory": exploratory,
        "provenance": "validated_analysis_artifact",
    }


def derive_metrics(result, manifest, spec):
    """Every number a person or model may cite, derived from the validated artifact."""
    labels = {arm["id"]: arm["label"] for arm in manifest["arms"]}
    comparison = result["comparison"]
    treatment, control = comparison["treatment"], comparison["control"]
    metrics = [
        _metric(
            "design.dataset",
            "Dataset",
            "Pinned public benchmark",
            "text",
            manifest["source"]["title"],
        ),
        _metric(
            "design.treatment_label",
            "Treatment arm",
            "Original campaign arm",
            "text",
            labels[treatment],
        ),
        _metric(
            "design.control_label", "Control arm", "Original campaign arm", "text", labels[control]
        ),
        _metric(
            "design.observation_window",
            "Observation window",
            "Publisher-described outcome window",
            "text",
            "the two weeks after the 2008 campaign",
        ),
        _metric("design.confidence_level", "Confidence level", "Interval level", "text", "95%"),
        _metric(
            "design.bootstrap_resamples",
            "Bootstrap resamples",
            "Seeded customer-level resamples",
            "count",
            spec["bootstrap"]["resamples"],
        ),
    ]
    for role, arm in (("treatment", treatment), ("control", control)):
        counts = result["arms"][arm]
        metrics.append(
            _metric(
                f"{role}.customers",
                f"Customers assigned to {labels[arm]}",
                "Assigned customers in the original arm (denominator)",
                "count",
                counts["n"],
                path=f"arms.{arm}.n",
            )
        )
        metrics.append(
            _metric(
                f"{role}.purchases",
                f"Purchases in {labels[arm]}",
                "Customers with conversion = 1 within the window",
                "count",
                counts["conversions"],
                path=f"arms.{arm}.conversions",
            )
        )
        metrics.append(
            _metric(
                f"{role}.visits",
                f"Site visits in {labels[arm]}",
                "Customers with visit = 1 within the window",
                "count",
                counts["visits"],
                path=f"arms.{arm}.visits",
            )
        )
        for outcome, noun in (("conversion", "purchase"), ("visit", "visit")):
            part = comparison[outcome][role]
            metrics.append(
                _metric(
                    f"{role}.{outcome}_rate",
                    f"{noun.capitalize()} rate, {labels[arm]}",
                    f"{noun.capitalize()}s divided by assigned customers",
                    "rate",
                    part["rate"],
                    unit="percent",
                    interval=part["interval"],
                    interval_method="wilson_score",
                    denominator={"events": part["events"], "n": part["n"]},
                    path=f"comparison.{outcome}.{role}",
                )
            )
        spend = comparison["spend"][role]
        metrics.append(
            _metric(
                f"{role}.spend_total",
                f"Measured spend, {labels[arm]}",
                "Sum of recorded spend over assigned customers",
                "currency",
                spend["total_cents"],
                unit="usd_cents",
                denominator={"n": spend["n"]},
                path=f"comparison.spend.{role}.total_cents",
            )
        )
        metrics.append(
            _metric(
                f"{role}.spend_per_customer",
                f"Spend per assigned customer, {labels[arm]}",
                "Total spend divided by all assigned customers, zero spend included",
                "currency",
                spend["mean_cents"],
                unit="usd_cents",
                denominator={"n": spend["n"]},
                path=f"comparison.spend.{role}.mean_cents",
            )
        )
    for outcome, noun in (("conversion", "purchase"), ("visit", "visit")):
        section = comparison[outcome]
        metrics.append(
            _metric(
                f"{outcome}.difference_pp",
                f"{noun.capitalize()} rate difference",
                f"{labels[treatment]} minus {labels[control]}, percentage points",
                "difference_pp",
                section["difference"],
                unit="percentage_points",
                interval=section["difference_interval"],
                interval_method="newcombe_hybrid_score",
                denominator={
                    "treatment_n": section["treatment"]["n"],
                    "control_n": section["control"]["n"],
                },
                path=f"comparison.{outcome}.difference",
            )
        )
        if section["relative_change"] is not None:
            metrics.append(
                _metric(
                    f"{outcome}.relative_change",
                    f"Relative change in {noun} rate",
                    "Difference divided by the control rate (defined only when control > 0)",
                    "relative_percent",
                    section["relative_change"],
                    unit="percent",
                    path=f"comparison.{outcome}.relative_change",
                )
            )
    spend = comparison["spend"]
    bootstrap = spend["bootstrap"]
    metrics.append(
        _metric(
            "spend.incremental_per_customer",
            "Estimated incremental historical spend per assigned customer",
            f"Mean spend per assigned customer, {labels[treatment]} minus {labels[control]}",
            "currency_difference",
            spend["difference_cents"],
            unit="usd_cents",
            interval=bootstrap["interval_cents"] if bootstrap else None,
            interval_method="customer_level_percentile_bootstrap" if bootstrap else None,
            denominator={
                "treatment_n": spend["treatment"]["n"],
                "control_n": spend["control"]["n"],
            },
            path="comparison.spend.difference_cents",
        )
    )
    if bootstrap:
        metrics.append(
            _metric(
                "spend.bootstrap_se",
                "Bootstrap standard error of the spend difference",
                "Standard deviation of the resampled differences",
                "currency",
                bootstrap["se_cents"],
                unit="usd_cents",
                path="comparison.spend.bootstrap.se_cents",
            )
        )
    for arm_id, counts in result["arms"].items():
        if arm_id in (treatment, control):
            continue
        metrics.append(
            _metric(
                f"source.{arm_id}.customers",
                f"Customers assigned to {labels[arm_id]} (not in this comparison)",
                "Third original arm, shown for the source overview only",
                "count",
                counts["n"],
                path=f"arms.{arm_id}.n",
            )
        )
        metrics.append(
            _metric(
                f"source.{arm_id}.conversion_rate",
                f"Purchase rate, {labels[arm_id]} (not in this comparison)",
                "Purchases divided by assigned customers; no interval, excluded from the plan",
                "rate",
                counts["conversions"] / counts["n"] if counts["n"] else None,
                unit="percent",
                denominator={"events": counts["conversions"], "n": counts["n"]},
                path=f"arms.{arm_id}",
            )
        )
    arm_for_role = {"treatment": treatment, "control": control}
    for breakdown, cells in result["exploratory"]["breakdowns"].items():
        for level, cell in cells.items():
            for role in ("treatment", "control"):
                part = cell[role]
                level_label = (
                    {"0": "existing customers", "1": "new customers"}.get(level, level)
                    if breakdown == "newbie"
                    else f"{level} channel"
                )
                metrics.append(
                    _metric(
                        f"exploratory.{breakdown}.{level.lower()}.{role}.conversion_rate",
                        f"Purchase rate, {labels[arm_for_role[role]]}, {level_label}",
                        "Exploratory descriptive breakdown; no interval; not confirmatory",
                        "rate",
                        part["rate"],
                        unit="percent",
                        denominator={"events": part["conversions"], "n": part["n"]},
                        path=f"exploratory.breakdowns.{breakdown}.{level}.{role}",
                        exploratory=True,
                    )
                )
    return metrics


def _percent(value, signed=False):
    text = f"{value * 100:.2f}%"
    return ("+" + text if signed and value > 0 else text) if value is not None else "undefined"


def _pp(value):
    return f"{value * 100:+.2f}"


def _money(cents_value, signed=False):
    if cents_value is None:
        return "undefined"
    rounded = int(round(cents_value))
    text = f"${abs(rounded) // 100:,}.{abs(rounded) % 100:02d}"
    if rounded < 0:
        return "-" + text
    return ("+" + text) if signed else text


def format_metric(metric):
    """Render one validated metric with its denominator and interval."""
    kind, value, interval = metric["kind"], metric["value"], metric["interval"]
    denominator = metric.get("denominator") or {}
    if value is None:
        return "undefined (empty group)"
    if kind == "text":
        return str(value)
    if kind == "count":
        return f"{value:,}"
    if kind == "rate":
        text = _percent(value)
        if "events" in denominator:
            text += f" ({denominator['events']:,} of {denominator['n']:,})"
        if interval:
            text += f"; 95% CI {_percent(interval[0])} to {_percent(interval[1])}"
        return text + (" [exploratory]" if metric.get("exploratory") else "")
    if kind == "difference_pp":
        text = f"{_pp(value)} percentage points"
        if interval:
            text += f" (95% CI {_pp(interval[0])} to {_pp(interval[1])})"
        return text
    if kind == "relative_percent":
        return _percent(value, signed=True)
    if kind == "currency":
        text = _money(value)
        if denominator.get("n") and metric["id"].endswith("spend_total"):
            text += f" across {denominator['n']:,} assigned customers"
        elif denominator.get("n"):
            text += f" per assigned customer ({denominator['n']:,} customers, zero spend included)"
        return text
    if kind == "currency_difference":
        text = _money(value, signed=True) + " per assigned customer"
        if interval:
            text += (
                f" (95% bootstrap CI {_money(interval[0], True)} to {_money(interval[1], True)})"
            )
        return text
    return str(value)


def render_text(text, metrics_by_id):
    """Replace placeholders with controller-formatted values; unknown ids are an error."""

    def substitute(match):
        metric = metrics_by_id.get(match.group(1))
        if metric is None:
            raise RunError("unknown_metric_id")
        return format_metric(metric)

    return PLACEHOLDER.sub(substitute, text)


def check_prose(text, path, metrics_by_id, *, contract="analysis"):
    """Placeholders must resolve; no raw numbers, ROI words or historical-contact actions."""
    for match in PLACEHOLDER.finditer(text):
        if match.group(1) not in metrics_by_id:
            raise ContractError(
                f"{contract}_contract_rejected",
                diagnostic(
                    "contract",
                    path,
                    expected="known metric id",
                    observed="unknown_metric_id",
                    known_metrics=sorted(metrics_by_id)[:20],
                ),
            )
    stripped = PLACEHOLDER.sub(" ", text)
    if _DIGIT_OR_SYMBOL.search(stripped):
        raise ContractError(
            f"{contract}_contract_rejected",
            diagnostic(
                "contract",
                path,
                expected="numbers only through [metric:ID] placeholders",
                observed="unsupported_quantity",
            ),
        )
    if _ROI_WORDS.search(stripped):
        raise ContractError(
            f"{contract}_contract_rejected",
            diagnostic(
                "contract",
                path,
                expected="no ROI, profit, guarantee or realized-outcome wording",
                observed="invented_roi_or_outcome",
            ),
        )
    for sentence in re.split(r"(?<=[.!?])\s+", stripped):
        if _CONTACT_VERBS.search(sentence) and _HISTORICAL_RECORDS.search(sentence):
            raise ContractError(
                f"{contract}_contract_rejected",
                diagnostic(
                    "contract",
                    path,
                    expected="no action that contacts the historical anonymous records",
                    observed="unauthorized_action",
                ),
            )
    return normalize(text)


def _contract_string(data, field, path, metrics_by_id, *, maximum):
    value = data.get(field)
    if not isinstance(value, str):
        raise ContractError(
            "analysis_contract_rejected",
            diagnostic("contract", path, expected="string", observed=observed_type(value)),
        )
    value = normalize(value)
    if not 1 <= len(value) <= maximum:
        raise ContractError(
            "analysis_contract_rejected",
            diagnostic(
                "contract", path, expected=f"1..{maximum} chars", observed=f"{len(value)} chars"
            ),
        )
    return check_prose(value, path, metrics_by_id)


def _contract_list(data, field, path, metrics_by_id, *, maximum_items, maximum, minimum_items=0):
    value = data.get(field)
    if not isinstance(value, list) or not minimum_items <= len(value) <= maximum_items:
        raise ContractError(
            "analysis_contract_rejected",
            diagnostic(
                "contract",
                path,
                expected=f"array of {minimum_items}..{maximum_items}",
                observed=observed_type(value),
            ),
        )
    return [
        _contract_string({"item": item}, "item", f"{path}[{index}]", metrics_by_id, maximum=maximum)
        for index, item in enumerate(value)
    ]


PROPOSAL_KEYS = {
    "hypothesis",
    "variant_a",
    "variant_b",
    "audience_requirements",
    "unit_of_randomization",
    "primary_outcome",
    "observation_window",
    "decision_rule",
    "missing_inputs",
}


def analysis_contract(content: str, metrics: list) -> dict:
    """Model reasoning JSON: interpretation, alternatives, unknowns and a next experiment.

    Every string may cite numbers only via `[metric:ID]`; the controller renders them.
    """
    name = "analysis"
    data = json_object(content, name)
    required = {
        "question_answered",
        "interpretation",
        "alternative_explanations",
        "unknowns",
        "proposed_next_experiment",
    }
    if set(data) != required:
        raise ContractError(
            "analysis_contract_rejected",
            diagnostic(
                "contract",
                "$",
                expected=sorted(required),
                observed="keys_mismatch",
                keys=sorted(str(k) for k in data)[:20],
            ),
        )
    by_id = {m["id"]: m for m in metrics}
    proposal = data["proposed_next_experiment"]
    if not isinstance(proposal, dict) or set(proposal) != PROPOSAL_KEYS:
        raise ContractError(
            "analysis_contract_rejected",
            diagnostic(
                "contract",
                "proposed_next_experiment",
                expected=sorted(PROPOSAL_KEYS),
                observed="keys_mismatch" if isinstance(proposal, dict) else observed_type(proposal),
            ),
        )
    prefix = "proposed_next_experiment."
    validated = {
        "question_answered": _contract_string(
            data, "question_answered", "question_answered", by_id, maximum=400
        ),
        "interpretation": _contract_string(
            data, "interpretation", "interpretation", by_id, maximum=1500
        ),
        "alternative_explanations": _contract_list(
            data,
            "alternative_explanations",
            "alternative_explanations",
            by_id,
            maximum_items=6,
            maximum=300,
            minimum_items=1,
        ),
        "unknowns": _contract_list(
            data, "unknowns", "unknowns", by_id, maximum_items=8, maximum=300, minimum_items=1
        ),
        "proposed_next_experiment": {
            "hypothesis": _contract_string(
                proposal, "hypothesis", prefix + "hypothesis", by_id, maximum=600
            ),
            "variant_a": _contract_string(
                proposal, "variant_a", prefix + "variant_a", by_id, maximum=400
            ),
            "variant_b": _contract_string(
                proposal, "variant_b", prefix + "variant_b", by_id, maximum=400
            ),
            "audience_requirements": _contract_list(
                proposal,
                "audience_requirements",
                prefix + "audience_requirements",
                by_id,
                maximum_items=8,
                maximum=240,
                minimum_items=1,
            ),
            "unit_of_randomization": _contract_string(
                proposal,
                "unit_of_randomization",
                prefix + "unit_of_randomization",
                by_id,
                maximum=100,
            ),
            "primary_outcome": _contract_string(
                proposal, "primary_outcome", prefix + "primary_outcome", by_id, maximum=200
            ),
            "observation_window": _contract_string(
                proposal, "observation_window", prefix + "observation_window", by_id, maximum=120
            ),
            "decision_rule": _contract_string(
                proposal, "decision_rule", prefix + "decision_rule", by_id, maximum=600
            ),
            "missing_inputs": _contract_list(
                proposal,
                "missing_inputs",
                prefix + "missing_inputs",
                by_id,
                maximum_items=10,
                maximum=240,
            ),
        },
    }
    used = sorted(
        {m.group(1) for text in _all_strings(validated) for m in PLACEHOLDER.finditer(text)}
    )
    validated["metric_ids_used"] = used
    return validated


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _all_strings(item)


def _optional_number(value, field, low, high):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise RunError(f"invalid_{field}")
    if not low <= value <= high:
        raise RunError(f"invalid_{field}")
    return value


def validate_proposal(data):
    """Human-editable next-experiment proposal with scenario and sample-size inputs."""
    if not isinstance(data, dict):
        raise RunError("invalid_proposal")
    allowed = PROPOSAL_KEYS | {"scenario_assumptions", "sample_size_inputs", "notes"}
    if set(data) != allowed:
        raise RunError("invalid_proposal")
    scenario = data["scenario_assumptions"]
    sample = data["sample_size_inputs"]
    if (
        not isinstance(scenario, dict)
        or set(scenario) != {"audience_size", "gross_margin", "campaign_cost_usd"}
        or not isinstance(sample, dict)
        or set(sample) != {"minimum_detectable_pp", "alpha", "power"}
    ):
        raise RunError("invalid_proposal")
    audience = scenario["audience_size"]
    if audience is not None and (type(audience) is not int or not 1 <= audience <= 100_000_000):
        raise RunError("invalid_audience_size")
    cost = scenario["campaign_cost_usd"]
    if cost is not None and (
        not isinstance(cost, str) or not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,2})?", cost)
    ):
        raise RunError("invalid_campaign_cost")
    return {
        "hypothesis": _text(data["hypothesis"], "hypothesis", maximum=600),
        "variant_a": _text(data["variant_a"], "variant_a", maximum=400),
        "variant_b": _text(data["variant_b"], "variant_b", maximum=400),
        "audience_requirements": _text_list(
            data["audience_requirements"], "audience_requirements", maximum_items=8, minimum_items=1
        ),
        "unit_of_randomization": _text(
            data["unit_of_randomization"], "unit_of_randomization", maximum=100
        ),
        "primary_outcome": _text(data["primary_outcome"], "primary_outcome", maximum=200),
        "observation_window": _text(data["observation_window"], "observation_window", maximum=120),
        "decision_rule": _text(data["decision_rule"], "decision_rule", maximum=600),
        "missing_inputs": _text_list(data["missing_inputs"], "missing_inputs", maximum_items=10),
        "scenario_assumptions": {
            "audience_size": audience,
            "gross_margin": _optional_number(scenario["gross_margin"], "gross_margin", 0, 1),
            "campaign_cost_usd": cost,
        },
        "sample_size_inputs": {
            "minimum_detectable_pp": _optional_number(
                sample["minimum_detectable_pp"], "minimum_detectable_pp", 0.0001, 100
            ),
            "alpha": _optional_number(sample["alpha"], "alpha", 0.0001, 0.5),
            "power": _optional_number(sample["power"], "power", 0.5, 0.9999),
        },
        "notes": _text(data["notes"], "notes", maximum=1500, allow_empty=True),
    }


def proposal_hash(content):
    return sha256(json.dumps(content, sort_keys=True).encode())


def validate_task_fields(data):
    if not isinstance(data, dict):
        raise RunError("invalid_task")
    title = _text(data.get("title"), "task_title", maximum=160)
    assignee = _text(data.get("assignee_label"), "task_assignee", maximum=80)
    action = _text(data.get("proposed_action"), "task_action", maximum=600)
    due = data.get("due_date")
    if due is not None and (
        not isinstance(due, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due)
    ):
        raise RunError("invalid_task_due_date")
    return {"title": title, "assignee_label": assignee, "proposed_action": action, "due_date": due}
