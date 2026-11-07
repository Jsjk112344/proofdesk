"""Reproducible synthetic dealer group. No real customers, dealers or vehicle identities."""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20261106
REFERENCE = datetime.fromisoformat("2026-11-06T08:00:00-07:00")
OUT = Path(__file__).resolve().parents[1] / "fixtures/dealer-group"
CITIES = [
    ("Salt Lake City", 40.76, -111.89),
    ("Sandy", 40.56, -111.84),
    ("Provo", 40.23, -111.66),
    ("Ogden", 41.22, -111.97),
    ("Orem", 40.30, -111.69),
    ("Lehi", 40.39, -111.85),
    ("St. George", 37.10, -113.58),
    ("Logan", 41.74, -111.83),
    ("Park City", 40.65, -111.50),
    ("Boise", 43.62, -116.20),
    ("Idaho Falls", 43.49, -112.04),
    ("Las Vegas", 36.17, -115.14),
    ("Henderson", 36.04, -114.98),
    ("Reno", 39.53, -119.81),
    ("Denver", 39.74, -104.99),
    ("Colorado Springs", 38.83, -104.82),
    ("Fort Collins", 40.59, -105.08),
    ("Grand Junction", 39.06, -108.55),
    ("Cheyenne", 41.14, -104.82),
    ("Pocatello", 42.87, -112.45),
    ("Twin Falls", 42.56, -114.46),
    ("Layton", 41.06, -111.97),
    ("Draper", 40.52, -111.86),
    ("West Valley", 40.69, -111.99),
]
MODELS = [
    ("Toyota", "RAV4 Hybrid", "XLE", "SUV", 36500),
    ("Toyota", "Camry", "SE", "sedan", 30500),
    ("Honda", "CR-V", "EX-L", "SUV", 34900),
    ("Honda", "Civic", "Sport", "sedan", 27900),
    ("Ford", "F-150", "XLT", "truck", 47900),
    ("Chevrolet", "Silverado 1500", "LT", "truck", 45900),
    ("Subaru", "Outback", "Premium", "wagon", 32900),
    ("Hyundai", "Tucson", "SEL", "SUV", 29900),
    ("Kia", "Sportage", "EX", "SUV", 31500),
    ("Toyota", "Highlander", "XLE", "SUV", 42500),
    ("Ford", "Escape", "Active", "SUV", 28500),
    ("Chevrolet", "Equinox", "LT", "SUV", 27900),
]
FIRST = [
    "Avery",
    "Jordan",
    "Morgan",
    "Taylor",
    "Riley",
    "Casey",
    "Drew",
    "Cameron",
    "Quinn",
    "Skyler",
    "Alex",
    "Parker",
    "Reese",
    "Sam",
    "Jamie",
    "Devon",
    "Blair",
    "Rowan",
    "Sage",
    "Robin",
]
LAST = ["Vale", "Mercer", "Hollis", "Finch", "Calder", "Wren", "Arden", "Ellis", "Linden", "Hart"]
SOURCES = ["OEM site", "third-party marketplace", "dealer website", "phone", "walk-in", "chat"]
# Different fictional operating conditions, not a display cap. Sandy's original
# records (including Maria) are preserved byte for byte.
RISK_COUNTS = [
    58,
    40,
    32,
    85,
    24,
    47,
    19,
    37,
    12,
    63,
    29,
    76,
    51,
    81,
    68,
    43,
    35,
    22,
    17,
    31,
    26,
    54,
    39,
    61,
]


def stamp(days=0, hours=0):
    return (REFERENCE - timedelta(days=days, hours=hours)).isoformat()


def vin(n):
    # Fictional manufacturer prefix, restricted VIN alphabet, real check-digit algorithm.
    base = "ZZZ" + f"{n:05d}" + "0" + "R" + "S" + f"{n:06d}"
    translit = dict(
        zip(
            "ABCDEFGHJKLMNPRSTUVWXYZ",
            [1, 2, 3, 4, 5, 6, 7, 8, 1, 2, 3, 4, 5, 7, 9, 2, 3, 4, 5, 6, 7, 8, 9],
        )
    )
    weights = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
    check = sum((int(c) if c.isdigit() else translit[c]) * w for c, w in zip(base, weights)) % 11
    return base[:8] + ("X" if check == 10 else str(check)) + base[9:]


def generate():
    rng = random.Random(SEED)
    roofs, inventory, leads = [], [], []
    for ix, (city, lat, lng) in enumerate(CITIES):
        rid = f"r{ix + 1:02d}"
        staff = [
            f"{FIRST[(ix + j) % len(FIRST)]} {LAST[(ix * 3 + j) % len(LAST)]}"
            for j in range(6 + ix % 7)
        ]
        roofs.append(
            dict(
                id=rid,
                name=f"Summit {city}",
                city=city,
                lat=lat,
                lng=lng,
                brand_mix="Toyota|Honda|Ford|Chevrolet|Subaru|Hyundai|Kia|used",
                manager=f"{FIRST[(ix + 4) % len(FIRST)]} {LAST[(ix + 2) % len(LAST)]}",
                salespeople="|".join(staff),
                data_label="Sample dealer group",
            )
        )
        for j in range(125):
            n = ix * 125 + j + 1
            make, model, trim, body, price = MODELS[j % len(MODELS)]
            year = rng.choice([2022, 2023, 2024, 2024, 2025, 2026])
            used = year < 2026
            age = rng.choices(
                [
                    rng.randint(1, 30),
                    rng.randint(31, 59),
                    rng.randint(60, 89),
                    rng.randint(90, 160),
                ],
                weights=[40, 25, 22, 13],
            )[0]
            price = price - (2026 - year) * 1300 + rng.randrange(-5, 6) * 100
            status = "sold" if j % 17 == 0 else ("in_transit" if j % 13 == 0 else "in_stock")
            inventory.append(
                dict(
                    stock_no=f"S{n:05d}",
                    vin=vin(n),
                    rooftop_id=rid,
                    condition="used" if used else "new",
                    year=year,
                    make=make,
                    model=model,
                    trim=trim,
                    body=body,
                    color=rng.choice(["blue", "silver", "white", "black", "red", "gray"]),
                    mileage=rng.randint(5000, 58000) if used else rng.randint(3, 90),
                    list_price=price,
                    cost=price - rng.randrange(1800, 4800, 100),
                    days_on_lot=age,
                    status=status,
                    eta=stamp(days=-rng.randint(1, 14)) if status == "in_transit" else "",
                    sold_date=stamp(days=rng.randint(1, 14)) if status == "sold" else "",
                    data_label="Sample dealer group",
                )
            )
        own = inventory[-125:]
        for j in range(475):
            historical = j >= 375
            source = SOURCES[j % len(SOURCES)]
            status = (
                (
                    "sold"
                    if rng.random() < (0.70 if source == "dealer website" else 0.18)
                    else "lost"
                )
                if historical
                else ("new" if j % 7 == 0 else ("appointment" if j % 19 == 0 else "contacted"))
            )
            # Exactly twenty-five cold open leads per rooftop before the hero override.
            cold = j < 25
            created = (
                rng.randint(5, 24)
                if cold
                else (rng.randint(2, 30) if not historical else rng.randint(30, 120))
            )
            last = stamp(hours=rng.randint(73, 180)) if cold else stamp(hours=rng.randint(1, 48))
            unit = own[(j * 7) % 125]
            if cold and j % 2 == 0:
                unit = own[(j // 2 * 17) % 125]
            interest = (
                unit["stock_no"]
                if j % 3
                else "|".join(str(unit[k]) for k in ["year", "make", "model", "trim", "color"])
            )
            response = rng.randint(480, 1800) if ix in (3, 13) else rng.randint(8, 150)
            leads.append(
                dict(
                    lead_id=f"L{ix * 475 + j + 1:06d}",
                    rooftop_id=rid,
                    customer=f"{FIRST[(ix + j * 3) % len(FIRST)]} {chr(65 + j % 26)}.",
                    source=source,
                    created_at=stamp(days=created),
                    last_contact_at=last,
                    first_contact_at=(
                        REFERENCE - timedelta(days=created) + timedelta(minutes=response)
                    ).isoformat(),
                    last_contact_channel=rng.choice(["SMS", "email", "phone"]),
                    assigned_salesperson=staff[j % len(staff)],
                    vehicle_of_interest=interest,
                    budget_min=unit["list_price"] - 6000,
                    budget_max=unit["list_price"] + 3000,
                    trade_in="2017|Honda|CR-V|85000" if j % 5 == 0 else "",
                    status=status,
                    appointment_at=stamp(days=2)
                    if status == "appointment" and j < 25
                    else (stamp(days=-1) if status == "appointment" else ""),
                    notes="Prefers an SUV; available after work."
                    if unit["body"] == "SUV"
                    else "Asked about availability and trade-in options.",
                    data_label="Sample dealer group",
                )
            )
    hero_sold, hero_match = inventory[125], inventory[137]
    for u in (hero_sold, hero_match):
        u.update(
            year=2024, make="Toyota", model="RAV4 Hybrid", trim="XLE", body="SUV", condition="used"
        )
    hero_sold.update(color="blue", status="sold", sold_date=stamp(days=6), eta="", days_on_lot=32)
    hero_match.update(
        color="silver",
        status="in_stock",
        sold_date="",
        eta="",
        days_on_lot=74,
        list_price=32900,
        cost=29500,
        mileage=18420,
    )
    leads[475].update(
        customer="Maria G.",
        created_at=stamp(days=9),
        last_contact_at=stamp(days=7),
        first_contact_at=stamp(days=9, hours=-1),
        vehicle_of_interest=hero_sold["stock_no"],
        trade_in="2017|Honda|CR-V|85000",
        budget_min=29000,
        budget_max=35000,
        status="contacted",
        notes="Interested in the blue RAV4 Hybrid XLE; has a CR-V to trade.",
    )
    by_stock = {u["stock_no"]: u for u in inventory}
    for ix, target in enumerate(RISK_COUNTS):
        if ix == 1:
            continue
        own = inventory[ix * 125 : (ix + 1) * 125]
        sold = next(u for u in own if u["status"] == "sold")
        available = [u for u in own if u["status"] == "in_stock"]
        cold_count = round(target * 0.62)
        for j, lead in enumerate(leads[ix * 475 : ix * 475 + 375]):
            lead["last_contact_at"] = (
                stamp(hours=96 + j % 72) if j < cold_count else stamp(hours=12 + j % 36)
            )
            if cold_count <= j < target:
                lead["vehicle_of_interest"] = sold["stock_no"]
            elif j >= target:
                wanted = by_stock.get(lead["vehicle_of_interest"])
                if wanted and wanted["status"] == "sold":
                    lead["vehicle_of_interest"] = available[j % len(available)]["stock_no"]
                if lead["status"] == "appointment":
                    lead["appointment_at"] = stamp(days=-1)
    return roofs, inventory, leads


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    roofs, inventory, leads = generate()
    for name, rows in [("rooftops", roofs), ("inventory", inventory), ("leads", leads)]:
        with (OUT / f"{name}.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    meta = dict(
        group="Summit Auto Group",
        data_label="Sample dealer group",
        synthetic=True,
        seed=SEED,
        reference_time=REFERENCE.isoformat(),
        floorplan_daily_rate=8.0,
        match_distance_miles=250,
        counts=dict(
            rooftops=len(roofs), inventory=len(inventory), open_leads=9000, historical_leads=2400
        ),
        assumption=(
            "Entered assumption: $8 per inventory unit per day, not a measured lending charge."
        ),
    )
    (OUT / "group.json").write_text(json.dumps(meta, indent=2) + "\n")
    # Actual prior-night input snapshot: contact/sold/arrival events after the cut are removed.
    cut = REFERENCE - timedelta(days=1)
    previous = json.loads(json.dumps(dict(rooftops=roofs, inventory=inventory, leads=leads)))
    for row in previous["inventory"]:
        row["days_on_lot"] = max(0, row["days_on_lot"] - 1)
        if row["sold_date"] and datetime.fromisoformat(row["sold_date"]) > cut:
            row.update(status="in_stock", sold_date="")
    for row in previous["leads"]:
        if datetime.fromisoformat(row["last_contact_at"]) > cut:
            row["last_contact_at"] = (cut - timedelta(hours=24)).isoformat()
    previous.update(reference_time=cut.isoformat(), data_label="Sample dealer group")
    (OUT / "previous-night.json").write_text(json.dumps(previous, separators=(",", ":")) + "\n")
    print(json.dumps(meta["counts"]))


if __name__ == "__main__":
    main()
