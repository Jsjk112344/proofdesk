"""Controller-side reconciliation and expansion, independent of the sandbox program."""

import copy
import math
import statistics
from datetime import datetime

from ..execution.artifacts import Rejected, sha256

UNIT_FIELDS = [
    "stock_no",
    "rooftop_id",
    "year",
    "make",
    "model",
    "trim",
    "body",
    "color",
    "mileage",
    "list_price",
    "cost",
    "days_on_lot",
    "status",
    "eta",
    "sold_date",
]
LEAD_FIELDS = [
    "lead_id",
    "rooftop_id",
    "status",
    "created_at",
    "last_contact_at",
    "first_contact_at",
    "source",
    "assigned_salesperson",
    "vehicle_of_interest",
    "budget_min",
    "budget_max",
    "appointment_at",
]
SCORE_NAMES = [
    "make",
    "model",
    "trim",
    "body",
    "year",
    "color",
    "budget",
    "mileage",
    "aged inventory",
    "same store",
]


def review_snapshot(group, at):
    """Advance review time without pretending an unchanged CSV is a live CRM feed.

    Synthetic timestamps move together so the published sample story stays relative
    to its review date. Uploaded timestamps remain source facts; inventory age advances
    by elapsed whole days since the export was imported.
    """
    from .ingestion import DATES

    snapshot = copy.deepcopy(group)
    current = datetime.fromisoformat(at)
    reference = datetime.fromisoformat(group["reference_time"])
    delta = current - reference
    snapshot["reference_time"] = at
    if group.get("synthetic"):
        blocks = [snapshot]
        if snapshot.get("previous"):
            blocks.append(snapshot["previous"])
            snapshot["previous"]["reference_time"] = (
                datetime.fromisoformat(group["previous"]["reference_time"]) + delta
            ).isoformat()
        for block in blocks:
            for row in block["leads"] + block["inventory"]:
                for key in set(row) & DATES:
                    if row.get(key):
                        row[key] = (datetime.fromisoformat(row[key]) + delta).isoformat()
    else:
        elapsed = max(0, delta.days)
        for unit in snapshot["inventory"]:
            if unit["status"] != "sold":
                unit["days_on_lot"] += elapsed
    return snapshot


def typed_input(group, rid, *, previous=False):
    content = group.get("previous") if previous else group
    if content is None:
        return None
    return dict(
        version=1,
        rooftop_id=rid,
        now=content["reference_time"],
        rate=group["floorplan_daily_rate"],
        distance=group["match_distance_miles"],
        rooftops=[[r["id"], r["lat"], r["lng"]] for r in content["rooftops"]],
        inventory=[[u.get(k, "") for k in UNIT_FIELDS] for u in content["inventory"]],
        leads=[
            [row.get(k, "") for k in LEAD_FIELDS]
            for row in content["leads"]
            if row["rooftop_id"] == rid
        ],
    )


def miles(a, b):
    lat1, lat2 = math.radians(a[1]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = math.radians(b[2] - a[2])
    return 7917.6 * math.asin(
        min(
            1,
            math.sqrt(
                math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            ),
        )
    )


def preference(lead, stock):
    interest = lead[8]
    if interest in stock:
        return stock[interest]
    parts = interest.split("|")
    if len(parts) >= 5:
        return ["", "", int(parts[0]), *parts[1:4], "", parts[4], 60000, 0, 0, 0, "", "", ""]
    return ["", "", 0, "", interest, "", "", "", 60000, 0, 0, 0, "", "", ""]


def score(lead, want, unit, rid):
    exact = [unit[k].casefold() == want[k].casefold() for k in (3, 4, 5)]
    return [
        int(exact[0]) * 20,
        int(exact[1]) * 25,
        int(exact[2]) * 10,
        8 if want[6] and want[6] == unit[6] else 0,
        max(0, 8 - 2 * abs(want[2] - unit[2])),
        2 if want[7] == unit[7] else 0,
        10 if lead[9] <= unit[9] <= lead[10] else 0,
        3 if unit[8] <= max(30000, want[8]) else 0,
        6 if unit[11] >= 60 else 0,
        8 if unit[1] == rid else 0,
    ]


def require(condition):
    if not condition:
        raise Rejected("dealer_result_reconciliation_failed")


def reconcile(result, data, raw):
    require(isinstance(result, dict) and set(result) == {"v", "h", "r", "a", "k", "s", "p"})
    require(result["v"] == 1 and result["h"] == sha256(raw))
    leads = data["leads"]
    units = data["inventory"]
    stock = {u[0]: u for u in units}
    rid = data["rooftop_id"]
    now = datetime.fromisoformat(data["now"])
    roofs = {r[0]: r for r in data["rooftops"]}
    near = {r for r in roofs if miles(roofs[rid], roofs[r]) <= data["distance"]}
    expected_risks = []
    responses = []
    staff = {}
    sources = {}
    nopen = 0
    ncold = 0
    napp = 0
    for i, lead in enumerate(leads):
        s = sources.setdefault(lead[6], [0, 0, 0])
        s[0] += 1
        s[1] += lead[2] == "sold"
        s[2] += lead[2] == "appointment"
        if lead[5]:
            value = max(
                0,
                (datetime.fromisoformat(lead[5]) - datetime.fromisoformat(lead[3])).total_seconds()
                / 60,
            )
            responses.append(value)
            staff.setdefault(lead[7], []).append(value)
        if lead[2] in ("sold", "lost"):
            continue
        nopen += 1
        napp += lead[2] == "appointment"
        gap = (now - datetime.fromisoformat(lead[4] or lead[3])).total_seconds() / 3600
        cold = gap >= 72
        ncold += cold
        want = preference(lead, stock)
        stale = lead[2] == "appointment" and lead[11] and datetime.fromisoformat(lead[11]) < now
        slow = not lead[5] and (now - datetime.fromisoformat(lead[3])).total_seconds() >= 14400
        flags = int(cold) + 2 * int(want[12] == "sold") + 4 * int(bool(stale)) + 8 * int(slow)
        if not flags:
            continue
        choices = []
        for j, unit in enumerate(units):
            if unit[1] not in near or unit[12] not in ("in_stock", "in_transit"):
                continue
            bits = score(lead, want, unit, rid)
            if bits[1] and sum(bits) >= 55:
                choices.append([j, bits])
        choices.sort(key=lambda c: (-sum(c[1]), units[c[0]][0]))
        expected_risks.append([i, flags, choices[:3]])
    require(result["r"] == expected_risks)
    aged = []
    for j, unit in enumerate(units):
        if unit[1] == rid and unit[12] == "in_stock" and unit[11] >= 60:
            count = sum(
                1
                for lead in leads
                if lead[2] not in ("sold", "lost")
                and (parts := score(lead, preference(lead, stock), unit, rid))[1]
                and sum(parts) >= 55
            )
            aged.append([j, count])
    require(result["a"] == aged)
    best = [units[r[2][0][0]] for r in expected_risks if r[2]]
    aged_indices = {
        j for _, _, candidates in expected_risks for j, _ in candidates if units[j][11] >= 60
    }
    expected = dict(
        open_leads=nopen,
        cold_leads=ncold,
        at_risk=len(expected_risks),
        matched_leads=len(best),
        matched_in_stock=sum(u[12] == "in_stock" for u in best),
        aged_matched=len(aged_indices),
        aged_60=len(aged),
        aged_90=sum(units[j][11] >= 90 for j, _ in aged),
        recoverable_gross=round(sum(u[9] - u[10] for u in best), 2),
        floorplan_daily=round(len(aged) * data["rate"], 2),
        floorplan_to_date=round(sum(units[j][11] * data["rate"] for j, _ in aged), 2),
        appointment_rate=round(napp / nopen, 4) if nopen else 0,
        median_response_minutes=round(statistics.median(responses), 1) if responses else None,
    )
    require(result["k"] == expected)
    require(result["s"] == [[k, *v] for k, v in sorted(sources.items())])
    require(result["p"] == [[k, round(statistics.median(v), 1)] for k, v in sorted(staff.items())])
    return {
        "status": "matched",
        "input_sha256": sha256(raw),
        "checks": [
            "risk flags",
            "top three scoring and distance",
            "KPI totals",
            "source and salesperson denominators",
            "aged inventory and costs",
        ],
    }


def expand(result, data, group):
    all_leads = {row["lead_id"]: row for row in group["leads"]}
    roofs = {r["id"]: r for r in group["rooftops"]}
    queue = []
    for idx, flags, matches in result["r"]:
        lead = all_leads[data["leads"][idx][0]]
        choices = []
        for j, parts in matches:
            unit = dict(zip(UNIT_FIELDS, data["inventory"][j]))
            unit.update(
                score=sum(parts),
                components=dict(zip(SCORE_NAMES, parts)),
                store_name=roofs[unit["rooftop_id"]]["name"],
                transfer=unit["rooftop_id"] != data["rooftop_id"],
            )
            choices.append(unit)
        wanted = preference(data["leads"][idx], {u[0]: u for u in data["inventory"]})
        interest = dict(zip(UNIT_FIELDS, wanted))
        queue.append(
            dict(
                lead_id=lead["lead_id"],
                customer=lead["customer"],
                first_name=lead["customer"].split()[0],
                salesperson=lead["assigned_salesperson"],
                trade_in=lead["trade_in"],
                created_at=lead["created_at"],
                last_contact_at=lead["last_contact_at"],
                wanted=interest,
                risks=[
                    name
                    for bit, name in [
                        (1, "Cold lead"),
                        (2, "Vehicle sold"),
                        (4, "Stale appointment"),
                        (8, "Slow response"),
                    ]
                    if flags & bit
                ],
                matches=choices,
                priority=100 * bool(flags & 2)
                + 50 * bool(flags & 1)
                + max([u["score"] for u in choices], default=0),
            )
        )
    queue.sort(key=lambda lead: (-lead["priority"], lead["lead_id"]))
    return dict(
        rooftop_id=data["rooftop_id"],
        metrics=result["k"],
        queue=queue,
        aged_inventory=[
            dict(
                zip(UNIT_FIELDS, data["inventory"][j]),
                matched_open_leads=count,
                floorplan_cost=round(data["inventory"][j][11] * data["rate"], 2),
            )
            for j, count in result["a"]
        ],
        sources=[
            dict(
                source=s,
                total=n,
                sold=sold,
                appointments=ap,
                close_rate=round(sold / n, 4) if n else 0,
            )
            for s, n, sold, ap in result["s"]
        ],
        salespeople=[dict(name=s, median_response_minutes=v) for s, v in result["p"]],
    )
