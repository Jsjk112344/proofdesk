"""Fixed, versioned analysis program executed inside the disposable sandbox.

It is self-contained (standard library only) and runs as the sandbox task: the first
input line is the dataset header, the second the saved analysis plan, the rest one row
per assigned customer (arm, visit, conversion, spend in integer cents, newbie, channel).
It computes counts, Wilson score intervals, the Newcombe hybrid score interval for the
rate difference, mean spend per assigned customer (zero-spend customers included) and a
seeded customer-level bootstrap for the spend difference. Output is deterministic for
identical input and seed; nothing is written except /work/out/result.json.

Bootstrap note: resampling n customers with replacement from an arm is equivalent to
drawing the number of buyer draws from Binomial(n, buyers/n) and then that many spends
uniformly with replacement from the buyers' spends; both give the same distribution of
the resampled mean, and the second form avoids resampling tens of thousands of zeros.
"""

import hashlib
import json
import math
import os
import random

PROGRAM_VERSION = "salesdesk-analysis-1"
RESULT_FORMAT = "salesdesk-analysis-result-1"
INPUT_FORMAT = "salesdesk-analysis-input-1"
Z = 1.959963984540054
MAX_RESAMPLES = 4000
WORK = os.environ.get("SALESDESK_WORK", "/work")


def wilson(events, n):
    if n == 0:
        return None
    p = events / n
    d = 1 + Z * Z / n
    c = p + Z * Z / (2 * n)
    r = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))
    return [(c - r) / d, (c + r) / d]


def newcombe(ea, na, eb, nb):
    a, b = wilson(ea, na), wilson(eb, nb)
    if a is None or b is None:
        return None
    pa, pb = ea / na, eb / nb
    d = pa - pb
    low = d - math.sqrt((pa - a[0]) ** 2 + (b[1] - pb) ** 2)
    high = d + math.sqrt((a[1] - pa) ** 2 + (pb - b[0]) ** 2)
    return [max(-1.0, low), min(1.0, high)]


def proportion(events, n):
    return {
        "events": events,
        "n": n,
        "rate": (events / n) if n else None,
        "interval": wilson(events, n),
        "interval_method": "wilson_score",
    }


def rate_comparison(et, nt, ec, nc):
    rt = et / nt if nt else None
    rc = ec / nc if nc else None
    return {
        "treatment": proportion(et, nt),
        "control": proportion(ec, nc),
        "difference": (rt - rc) if rt is not None and rc is not None else None,
        "difference_interval": newcombe(et, nt, ec, nc),
        "difference_method": "newcombe_hybrid_score",
        "relative_change": ((rt - rc) / rc) if rt is not None and rc else None,
        "level": 0.95,
    }


def percentile(sorted_values, q):
    """Linear interpolation between order statistics (deterministic)."""
    if not sorted_values:
        return None
    position = q * (len(sorted_values) - 1)
    low = int(math.floor(position))
    high = min(low + 1, len(sorted_values) - 1)
    weight = position - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def bootstrap(spends_t, nt, spends_c, nc, seed, resamples):
    """Seeded customer-level bootstrap of mean spend difference in cents."""
    if nt == 0 or nc == 0:
        return None
    rng = random.Random(seed)
    kt, kc = len(spends_t), len(spends_c)
    pt, pc = kt / nt, kc / nc
    replicates = []
    for _ in range(resamples):
        mt = rng.binomialvariate(nt, pt) if kt else 0
        total_t = sum(rng.choices(spends_t, k=mt)) if mt else 0
        mc = rng.binomialvariate(nc, pc) if kc else 0
        total_c = sum(rng.choices(spends_c, k=mc)) if mc else 0
        replicates.append(total_t / nt - total_c / nc)
    ordered = sorted(replicates)
    mean = sum(replicates) / len(replicates)
    variance = sum((r - mean) ** 2 for r in replicates) / max(1, len(replicates) - 1)
    digest = hashlib.sha256(json.dumps(replicates).encode()).hexdigest()
    return {
        "method": "customer_level_percentile_bootstrap",
        "seed": seed,
        "resamples": resamples,
        "interval_cents": [percentile(ordered, 0.025), percentile(ordered, 0.975)],
        "se_cents": math.sqrt(variance),
        "replicate_mean_cents": mean,
        "replicates_sha256": digest,
        "assumptions": [
            "customers are independent within each original arm",
            "resampling within arm preserves the original assignment",
            "percentile interval; skewed zero-heavy spend makes the interval approximate",
        ],
    }


def main():
    with open(os.path.join(WORK, "input.txt"), "rb") as stream:
        raw = stream.read()
    input_sha256 = hashlib.sha256(raw).hexdigest()
    lines = raw.decode("utf-8").split("\n")
    header = json.loads(lines[0])
    plan_line = lines[1]
    plan = json.loads(plan_line)
    if header.get("format") != INPUT_FORMAT:
        raise SystemExit("unexpected_input_format")
    arms_by_code = {int(k): v for k, v in header["arms"].items()}
    channels = {int(k): v for k, v in header["channels"].items()}
    treatment, control = plan["comparison"]["treatment"], plan["comparison"]["control"]
    if treatment not in arms_by_code.values() or control not in arms_by_code.values():
        raise SystemExit("unknown_arm")
    if treatment == control:
        raise SystemExit("identical_arms")
    seed, resamples = plan["bootstrap"]["seed"], plan["bootstrap"]["resamples"]
    if type(seed) is not int or type(resamples) is not int or not 1 <= resamples <= MAX_RESAMPLES:
        raise SystemExit("invalid_bootstrap_settings")
    breakdowns = plan.get("exploratory_breakdowns", [])
    arms = {
        name: {"n": 0, "visits": 0, "conversions": 0, "spend_cents": 0, "buyers": 0, "spends": []}
        for name in arms_by_code.values()
    }
    exploratory = {b: {} for b in breakdowns}
    rows_read = 0
    for line in lines[2:]:
        if not line:
            continue
        arm_code, visit, conversion, spend, newbie, channel = line.split(",")
        arm = arms[arms_by_code[int(arm_code)]]
        visit, conversion, spend = int(visit), int(conversion), int(spend)
        if visit not in (0, 1) or conversion not in (0, 1) or spend < 0:
            raise SystemExit("row_rejected")
        arm["n"] += 1
        arm["visits"] += visit
        arm["conversions"] += conversion
        arm["spend_cents"] += spend
        if spend > 0:
            arm["buyers"] += 1
            arm["spends"].append(spend)
        rows_read += 1
        name = arms_by_code[int(arm_code)]
        if name in (treatment, control):
            role = "treatment" if name == treatment else "control"
            for breakdown in breakdowns:
                level = newbie if breakdown == "newbie" else channels[int(channel)]
                cell = exploratory[breakdown].setdefault(
                    str(level),
                    {
                        "treatment": {"n": 0, "conversions": 0},
                        "control": {"n": 0, "conversions": 0},
                    },
                )
                cell[role]["n"] += 1
                cell[role]["conversions"] += conversion
    if rows_read != header["rows"]:
        raise SystemExit("row_count_mismatch")
    t, c = arms[treatment], arms[control]
    spend_boot = bootstrap(t["spends"], t["n"], c["spends"], c["n"], seed, resamples)
    mean_t = t["spend_cents"] / t["n"] if t["n"] else None
    mean_c = c["spend_cents"] / c["n"] if c["n"] else None
    for breakdown in exploratory.values():
        for cell in breakdown.values():
            for role in ("treatment", "control"):
                part = cell[role]
                part["rate"] = part["conversions"] / part["n"] if part["n"] else None
    result = {
        "format": RESULT_FORMAT,
        "program_version": PROGRAM_VERSION,
        "dataset_id": header["dataset_id"],
        "dataset_raw_sha256": header["raw_sha256"],
        "analysis_input_sha256": input_sha256,
        "plan_sha256": hashlib.sha256(plan_line.encode("utf-8")).hexdigest(),
        "rows_read": rows_read,
        "arms": {
            name: {k: v for k, v in counts.items() if k != "spends"}
            for name, counts in arms.items()
        },
        "comparison": {
            "treatment": treatment,
            "control": control,
            "conversion": rate_comparison(t["conversions"], t["n"], c["conversions"], c["n"]),
            "visit": rate_comparison(t["visits"], t["n"], c["visits"], c["n"]),
            "spend": {
                "treatment": {"n": t["n"], "total_cents": t["spend_cents"], "mean_cents": mean_t},
                "control": {"n": c["n"], "total_cents": c["spend_cents"], "mean_cents": mean_c},
                "difference_cents": (
                    (mean_t - mean_c) if mean_t is not None and mean_c is not None else None
                ),
                "denominator": "all assigned customers, including zero spend",
                "bootstrap": spend_boot,
            },
        },
        "exploratory": {
            "label": "exploratory_descriptive_only",
            "breakdowns": exploratory,
            "note": (
                "Pre-declared descriptive breakdowns of the planned comparison; "
                "no intervals, not confirmatory."
            ),
        },
    }
    out_dir = os.path.join(WORK, "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "result.json"), "w", encoding="utf-8") as stream:
        stream.write(json.dumps(result, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
