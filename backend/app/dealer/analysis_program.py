"""Fixed standard-library dealer analysis; executed only in a disposable Docker sandbox.

Compact indexed output keeps the existing 16 KiB artifact limit. Indices resolve only
against the hash-bound typed input; the controller reconciles all values before use.
"""

import hashlib
import json
import math
import statistics
from datetime import datetime
from pathlib import Path


def distance(a, b):
    a1, b1, a2, b2 = map(math.radians, [a[1], a[2], b[1], b[2]])
    return (
        3958.8
        * 2
        * math.asin(
            min(
                1,
                math.sqrt(
                    math.sin((a2 - a1) / 2) ** 2
                    + math.cos(a1) * math.cos(a2) * math.sin((b2 - b1) / 2) ** 2
                ),
            )
        )
    )


def desired(interest, by_stock):
    if interest in by_stock:
        return by_stock[interest]
    parts = interest.split("|")
    if len(parts) >= 5:
        return [
            "",
            "",
            int(parts[0]),
            parts[1],
            parts[2],
            parts[3],
            "",
            parts[4],
            60000,
            0,
            0,
            0,
            "",
            "",
            "",
        ]
    return ["", "", 0, "", interest, "", "", "", 60000, 0, 0, 0, "", "", ""]


def components(lead, wanted, unit, rid):
    return [
        20 * int(unit[3].casefold() == wanted[3].casefold()),
        25 * int(unit[4].casefold() == wanted[4].casefold()),
        10 * int(unit[5].casefold() == wanted[5].casefold()),
        8 * int(bool(wanted[6]) and unit[6] == wanted[6]),
        max(0, 8 - abs(unit[2] - wanted[2]) * 2),
        2 * int(unit[7] == wanted[7]),
        10 * int(lead[9] <= unit[9] <= lead[10]),
        3 * int(unit[8] <= max(wanted[8], 30000)),
        6 * int(unit[11] >= 60),
        8 * int(unit[1] == rid),
    ]


def analyze(data):
    units = data["inventory"]
    leads = data["leads"]
    rid = data["rooftop_id"]
    now = datetime.fromisoformat(data["now"])
    roofs = {r[0]: r for r in data["rooftops"]}
    by_stock = {u[0]: u for u in units}
    nearby = {r for r in roofs if distance(roofs[rid], roofs[r]) <= data["distance"]}
    available = [
        (i, u)
        for i, u in enumerate(units)
        if u[1] in nearby and u[12] in ("in_stock", "in_transit")
    ]
    risks = []
    response = []
    sales = {}
    sources = {}
    aged_matches = {}
    cold = 0
    matched_stock = 0
    opened = 0
    appointments = 0
    gross = 0
    for i, lead in enumerate(leads):
        source = sources.setdefault(lead[6], [0, 0, 0])
        source[0] += 1
        source[1] += int(lead[2] == "sold")
        source[2] += int(lead[2] == "appointment")
        if lead[5]:
            mins = max(
                0,
                (datetime.fromisoformat(lead[5]) - datetime.fromisoformat(lead[3])).total_seconds()
                / 60,
            )
            response.append(mins)
            sales.setdefault(lead[7], []).append(mins)
        if lead[2] in ("sold", "lost"):
            continue
        opened += 1
        appointments += int(lead[2] == "appointment")
        gap = (now - datetime.fromisoformat(lead[4] or lead[3])).total_seconds() / 3600
        mask = int(gap >= 72)
        cold += mask
        wanted = desired(lead[8], by_stock)
        if wanted[12] == "sold":
            mask |= 2
        if lead[2] == "appointment" and lead[11] and datetime.fromisoformat(lead[11]) < now:
            mask |= 4
        if not lead[5] and (now - datetime.fromisoformat(lead[3])).total_seconds() >= 4 * 3600:
            mask |= 8
        if not mask:
            continue
        candidates = []
        for j, unit in available:
            c = components(lead, wanted, unit, rid)
            if sum(c) >= 55 and c[1]:
                candidates.append([j, c])
        candidates.sort(key=lambda c: (-sum(c[1]), units[c[0]][0]))
        best = candidates[:3]
        risks.append([i, mask, best])
        if best:
            unit = units[best[0][0]]
            gross += max(0, unit[9] - unit[10])
            matched_stock += int(unit[12] == "in_stock")
            for j, _ in best:
                if units[j][11] >= 60:
                    aged_matches.setdefault(j, set()).add(i)
    # Aged inventory's matched-open-lead count includes every open lead, not only risk.
    aged = []
    for j, unit in enumerate(units):
        if unit[1] != rid or unit[12] != "in_stock" or unit[11] < 60:
            continue
        count = 0
        for lead in leads:
            if lead[2] in ("sold", "lost"):
                continue
            wanted = desired(lead[8], by_stock)
            c = components(lead, wanted, unit, rid)
            count += int(c[1] > 0 and sum(c) >= 55)
        aged.append([j, count])
    return {
        "v": 1,
        "r": risks,
        "a": aged,
        "k": dict(
            open_leads=opened,
            cold_leads=cold,
            at_risk=len(risks),
            matched_leads=sum(bool(r[2]) for r in risks),
            matched_in_stock=matched_stock,
            aged_matched=len(aged_matches),
            aged_60=len(aged),
            aged_90=sum(units[j][11] >= 90 for j, _ in aged),
            recoverable_gross=round(gross, 2),
            floorplan_daily=round(len(aged) * data["rate"], 2),
            floorplan_to_date=round(sum(units[j][11] * data["rate"] for j, _ in aged), 2),
            appointment_rate=round(appointments / opened, 4) if opened else 0,
            median_response_minutes=round(statistics.median(response), 1) if response else None,
        ),
        "s": [[key, *value] for key, value in sorted(sources.items())],
        "p": [[key, round(statistics.median(value), 1)] for key, value in sorted(sales.items())],
    }


if __name__ == "__main__":
    raw = Path("/work/input.txt").read_bytes()
    result = analyze(json.loads(raw))
    result["h"] = hashlib.sha256(raw).hexdigest()
    Path("/work/out/result.json").write_text(
        json.dumps(result, separators=(",", ":"), sort_keys=True)
    )
