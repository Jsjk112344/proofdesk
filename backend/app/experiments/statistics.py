"""Controller-side statistics: Wilson and Newcombe intervals, scenario projection, sample size.

These functions are the independent implementation used to reconcile the sandboxed
analysis program's output and to compute scenario projections from entered assumptions.
They never see raw rows; they work on counts, sums and validated metric values.

References (formulas, no code copied):
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical
  inference. JASA 22, 209-212.
- Newcombe, R. G. (1998). Interval estimation for the difference between independent
  proportions: comparison of eleven methods. Statistics in Medicine 17, 873-890
  (method 10, the hybrid score interval).
"""

import math
from decimal import ROUND_HALF_UP, Decimal
from statistics import NormalDist

Z_95 = 1.959963984540054
CONFIDENCE_LEVEL = 0.95


def wilson_interval(events: int, n: int, z: float = Z_95):
    """Wilson score interval for a binomial proportion; None when the group is empty."""
    if type(events) is not int or type(n) is not int or n < 0 or not 0 <= events <= n:
        raise ValueError("invalid_counts")
    if n == 0:
        return None
    p = events / n
    denominator = 1 + z * z / n
    centre = p + z * z / (2 * n)
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - radius) / denominator, (centre + radius) / denominator)


def newcombe_difference(events_a: int, n_a: int, events_b: int, n_b: int, z: float = Z_95):
    """Newcombe hybrid score (method 10) interval for p_a - p_b; None if a group is empty."""
    a = wilson_interval(events_a, n_a, z)
    b = wilson_interval(events_b, n_b, z)
    if a is None or b is None:
        return None
    p_a, p_b = events_a / n_a, events_b / n_b
    difference = p_a - p_b
    low = difference - math.sqrt((p_a - a[0]) ** 2 + (b[1] - p_b) ** 2)
    high = difference + math.sqrt((a[1] - p_a) ** 2 + (p_b - b[0]) ** 2)
    return (max(-1.0, low), min(1.0, high))


def relative_change(rate_treatment: float, rate_control: float):
    """Relative change of the treatment rate over the control rate; undefined at zero."""
    if rate_control is None or rate_treatment is None or rate_control <= 0:
        return None
    return (rate_treatment - rate_control) / rate_control


def proportion_summary(events: int, n: int):
    interval = wilson_interval(events, n)
    return {
        "events": events,
        "n": n,
        "rate": (events / n) if n else None,
        "interval": list(interval) if interval else None,
        "interval_method": "wilson_score",
        "level": CONFIDENCE_LEVEL,
    }


def difference_summary(events_a, n_a, events_b, n_b):
    interval = newcombe_difference(events_a, n_a, events_b, n_b)
    rate_a = events_a / n_a if n_a else None
    rate_b = events_b / n_b if n_b else None
    return {
        "difference": (rate_a - rate_b) if rate_a is not None and rate_b is not None else None,
        "interval": list(interval) if interval else None,
        "interval_method": "newcombe_hybrid_score",
        "level": CONFIDENCE_LEVEL,
        "relative_change": relative_change(rate_a, rate_b),
    }


def cents(value) -> int:
    """Exact integer cents from a decimal currency string; rejects non-finite or negative."""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("currency_type")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("currency_value")
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValueError("currency_precision")
    return int((amount * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def usd(cents_value: int) -> str:
    """Exact decimal string for integer cents."""
    sign = "-" if cents_value < 0 else ""
    value = abs(int(cents_value))
    return f"{sign}{value // 100}.{value % 100:02d}"


def _finite_fraction(value, low, high):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (math.isfinite(value) and low <= value <= high)
    )


def project_scenario(incremental_cents_per_customer, interval_cents, assumptions):
    """Projected contribution from entered assumptions; every required input must be present.

    Projection = incremental revenue per customer × audience size × gross margin − campaign
    cost. Uncertainty is carried linearly from the historical bootstrap interval. The
    transfer assumption (a current audience behaves like the 2008 benchmark population
    under the same treatment) is disclosed, not established. Nothing here is realized.
    """
    required = ("audience_size", "gross_margin", "campaign_cost_usd")
    missing = [key for key in required if assumptions.get(key) is None]
    if missing:
        return {"available": False, "missing_inputs": missing}
    audience = assumptions["audience_size"]
    margin = assumptions["gross_margin"]
    cost = assumptions["campaign_cost_usd"]
    if (
        type(audience) is not int
        or not 1 <= audience <= 100_000_000
        or not _finite_fraction(margin, 0, 1)
        or not isinstance(cost, str)
    ):
        raise ValueError("invalid_scenario_assumptions")
    cost_cents = cents(cost)
    point = incremental_cents_per_customer * audience
    low = interval_cents[0] * audience
    high = interval_cents[1] * audience
    contribution = point * margin - cost_cents
    contribution_low = low * margin - cost_cents
    contribution_high = high * margin - cost_cents
    roi = None if cost_cents == 0 else contribution / cost_cents
    roi_interval = (
        None if cost_cents == 0 else [contribution_low / cost_cents, contribution_high / cost_cents]
    )
    return {
        "available": True,
        "missing_inputs": [],
        "assumptions": {
            "audience_size": audience,
            "gross_margin": margin,
            "campaign_cost_usd": usd(cost_cents),
        },
        "projected_incremental_revenue_usd": usd(round(point)),
        "projected_incremental_revenue_interval_usd": [usd(round(low)), usd(round(high))],
        "projected_contribution_usd": usd(round(contribution)),
        "projected_contribution_interval_usd": [
            usd(round(contribution_low)),
            usd(round(contribution_high)),
        ],
        "projected_roi": roi,
        "projected_roi_interval": roi_interval,
        "roi_note": (
            "ROI is undefined because the entered campaign cost is zero."
            if cost_cents == 0
            else "Projected, not realized: contribution divided by entered campaign cost."
        ),
        "transfer_assumption": (
            "Assumes a current audience responds like the 2008 benchmark population to the "
            "same kind of treatment, and that the historical bootstrap interval transfers "
            "linearly. Neither is established by this analysis."
        ),
        "label": "scenario_assumption_not_measurement",
    }


def required_sample_size(p_control, minimum_detectable_pp, alpha, power):
    """Customers per arm for a two-proportion test (pooled normal approximation).

    Every input must be supplied explicitly; conventional values are never substituted.
    """
    if not (
        _finite_fraction(p_control, 0, 1)
        and _finite_fraction(minimum_detectable_pp, 0.0001, 100)
        and _finite_fraction(alpha, 0.0001, 0.5)
        and _finite_fraction(power, 0.5, 0.9999)
    ):
        raise ValueError("invalid_sample_size_inputs")
    p1 = p_control
    p2 = p_control + minimum_detectable_pp / 100
    if not 0 < p2 < 1 or not 0 < p1 < 1:
        raise ValueError("invalid_sample_size_inputs")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - alpha / 2)
    z_beta = normal.inv_cdf(power)
    pooled = (p1 + p2) / 2
    numerator = (
        z_alpha * math.sqrt(2 * pooled * (1 - pooled))
        + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    ) ** 2
    n = numerator / (p2 - p1) ** 2
    return {
        "per_arm": math.ceil(n),
        "total_two_arms": 2 * math.ceil(n),
        "inputs": {
            "control_rate": p_control,
            "minimum_detectable_pp": minimum_detectable_pp,
            "alpha": alpha,
            "power": power,
        },
        "method": "two_proportion_pooled_normal_approximation",
        "note": (
            "Approximate; assumes equal allocation and independent customers. Small rates "
            "and small effects need large samples; confirm with the final design."
        ),
    }
