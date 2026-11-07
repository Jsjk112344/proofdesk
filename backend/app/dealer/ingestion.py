"""Bounded untrusted CSV ingestion. No raw export is sent to inference or committed."""

import csv
import io
import math
import re
from datetime import UTC, datetime, timedelta

from ..execution.controller import ROOT
from ..execution.runner import RunError

MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50_000
SAMPLE = ROOT / "fixtures/dealer-group"
SYNONYMS = {
    "id": ["store id", "dealer id", "rooftop id"],
    "name": ["store name", "dealership", "dealer name"],
    "manager": ["store manager", "general manager"],
    "lat": ["latitude"],
    "lng": ["longitude", "lon"],
    "stock_no": ["stock number", "stock #", "stock", "stockno"],
    "rooftop_id": ["store id", "dealer id", "rooftop", "dealer code"],
    "condition": ["new/used", "new used", "type"],
    "list_price": ["asking price", "internet price", "sale price", "price", "msrp"],
    "cost": ["invoice", "unit cost", "dealer cost"],
    "days_on_lot": ["age", "days in stock", "inventory age", "days in inventory"],
    "lead_id": ["lead number", "opportunity id", "customer id", "prospect id"],
    "customer": ["customer name", "name", "prospect name"],
    "source": ["lead source", "provider"],
    "created_at": ["date created", "created date", "lead date", "received"],
    "last_contact_at": ["last activity", "last contact", "last contacted"],
    "first_contact_at": ["first response", "first contact"],
    "assigned_salesperson": ["salesperson", "sales rep", "assigned to", "owner"],
    "vehicle_of_interest": ["vehicle", "desired vehicle", "vehicle interest", "interested stock"],
    "budget_min": ["min budget", "budget low"],
    "budget_max": ["max budget", "budget high"],
    "trade_in": ["trade", "trade vehicle"],
    "status": ["lead status", "inventory status"],
    "eta": ["arrival date", "expected arrival"],
    "sold_date": ["date sold"],
    "appointment_at": ["appointment date"],
}
FIELDS = {
    "rooftops": ["id", "name", "city", "lat", "lng", "brand_mix", "manager", "salespeople"],
    "inventory": [
        "stock_no",
        "vin",
        "rooftop_id",
        "condition",
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
    ],
    "leads": [
        "lead_id",
        "rooftop_id",
        "customer",
        "source",
        "created_at",
        "last_contact_at",
        "first_contact_at",
        "last_contact_channel",
        "assigned_salesperson",
        "vehicle_of_interest",
        "budget_min",
        "budget_max",
        "trade_in",
        "status",
        "appointment_at",
        "notes",
    ],
}
REQUIRED = {
    "rooftops": {"id", "name", "city", "lat", "lng", "manager"},
    "inventory": {
        "stock_no",
        "rooftop_id",
        "year",
        "make",
        "model",
        "list_price",
        "cost",
        "days_on_lot",
        "status",
    },
    "leads": {
        "lead_id",
        "rooftop_id",
        "customer",
        "source",
        "created_at",
        "last_contact_at",
        "assigned_salesperson",
        "vehicle_of_interest",
        "budget_min",
        "budget_max",
        "status",
    },
}
NUMBERS = {
    "lat": (-90, 90),
    "lng": (-180, 180),
    "year": (1980, 2035),
    "mileage": (0, 1000000),
    "list_price": (0, 1000000),
    "cost": (0, 1000000),
    "days_on_lot": (0, 10000),
    "budget_min": (0, 1000000),
    "budget_max": (0, 1000000),
}
DATES = {"created_at", "last_contact_at", "first_contact_at", "eta", "sold_date", "appointment_at"}


def normalize(value):
    return re.sub("[^a-z0-9]", "", value.casefold())


def template(kind):
    if kind not in FIELDS:
        raise RunError("dealer_not_found")
    return ",".join(FIELDS[kind]) + "\n"


def parse_csv(kind, raw):
    if kind not in FIELDS:
        raise RunError("invalid_csv_kind")
    if len(raw) > MAX_BYTES:
        raise RunError("csv_file_too_large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise RunError("csv_utf8_required") from None
    if "\x00" in text:
        raise RunError("csv_nul_rejected")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    headers = reader.fieldnames or []
    if len(headers) > 80 or not headers:
        raise RunError("invalid_csv_headers")
    lookup = {
        normalize(alias): key for key in FIELDS[kind] for alias in [key, *SYNONYMS.get(key, [])]
    }
    mapping = {
        header: lookup[normalize(header)] for header in headers if normalize(header) in lookup
    }
    if len(set(mapping.values())) != len(mapping):
        raise RunError("csv_ambiguous_headers")
    missing = REQUIRED[kind] - set(mapping.values())
    if missing:
        raise RunError("csv_missing_headers:" + ",".join(sorted(missing)))
    rows, details, seen = [], [], set()
    total = 0
    try:
        for total, row in enumerate(reader, start=1):
            if total > MAX_ROWS:
                raise RunError("csv_row_limit")
            value = {key: "" for key in FIELDS[kind]}
            errors = []
            if None in row:
                errors.append("extra_columns")
            for header, key in mapping.items():
                cell = (row.get(header) or "").strip()
                if len(cell) > 500 or any(ord(c) < 32 and c not in "\t" for c in cell):
                    errors.append(key + ":invalid_text")
                value[key] = cell[:500]
            for key in REQUIRED[kind]:
                if not value[key] and not (kind == "leads" and key == "last_contact_at"):
                    errors.append(key + ":required")
            for key in set(value) & NUMBERS.keys():
                if not value[key] and key == "mileage":
                    value[key] = 0
                try:
                    num = float(value[key])
                    low, high = NUMBERS[key]
                    if not math.isfinite(num) or not low <= num <= high:
                        raise ValueError
                    if key in ("year", "mileage", "days_on_lot") and num != int(num):
                        raise ValueError
                    value[key] = int(num) if key in ("year", "mileage", "days_on_lot") else num
                except (ValueError, TypeError):
                    errors.append(key + ":invalid_number")
            for key in set(value) & DATES:
                if value[key]:
                    try:
                        date = datetime.fromisoformat(value[key].replace("Z", "+00:00"))
                        if date.tzinfo is None:
                            date = date.replace(tzinfo=UTC)
                        value[key] = date.isoformat()
                    except ValueError:
                        errors.append(key + ":invalid_date")
            identity = value.get("id") or value.get("lead_id") or value.get("stock_no")
            if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", identity or ""):
                errors.append("id:invalid")
            if identity in seen:
                errors.append("id:duplicate")
            seen.add(identity)
            if kind == "inventory":
                if value["status"] not in ("in_stock", "in_transit", "sold"):
                    errors.append("status:invalid")
                if value["status"] == "in_transit" and not value["eta"]:
                    errors.append("eta:required")
                if value["status"] == "sold" and not value["sold_date"]:
                    errors.append("sold_date:required")
                if value["vin"] and not re.fullmatch("[A-HJ-NPR-Z0-9]{17}", value["vin"]):
                    errors.append("vin:invalid")
                if not value["body"]:
                    value["body"] = "vehicle"
            if kind == "leads":
                if value["status"] not in ("new", "contacted", "appointment", "sold", "lost"):
                    errors.append("status:invalid")
                if (
                    isinstance(value["budget_min"], (int, float))
                    and isinstance(value["budget_max"], (int, float))
                    and value["budget_min"] > value["budget_max"]
                ):
                    errors.append("budget:reversed")
                # Contact details remain outside the product: first name and last initial only.
                parts = value["customer"].split()
                value["customer"] = (
                    parts[0] + (" " + parts[-1][0] + "." if len(parts) > 1 else "") if parts else ""
                )
            if errors:
                if len(details) < 100:
                    details.append({"row": total + 1, "errors": errors})
            else:
                rows.append(value)
    except (csv.Error, OverflowError):
        raise RunError("csv_malformed") from None
    if not total:
        raise RunError("csv_empty")
    return rows, dict(
        file=kind,
        rows=total,
        accepted=len(rows),
        rejected=total - len(rows),
        mapped_headers=mapping,
        details=details,
    )


def validate_group(rooftops, inventory, leads):
    ids = {r["id"] for r in rooftops}
    if not 1 <= len(ids) <= 100:
        raise RunError("rooftop_limit")
    if any(row["rooftop_id"] not in ids for row in inventory + leads):
        raise RunError("csv_unknown_rooftop")
    return dict(rooftops=rooftops, inventory=inventory, leads=leads)


def sample_group(at=None):
    import json

    meta = json.loads((SAMPLE / "group.json").read_text())
    rows = {}
    reports = []
    for kind in FIELDS:
        rows[kind], report = parse_csv(kind, (SAMPLE / f"{kind}.csv").read_bytes())
        reports.append(report)
    group = validate_group(**rows)
    group.update(meta)
    if at is not None:
        delta = at - datetime.fromisoformat(meta["reference_time"])
        for row in group["leads"] + group["inventory"]:
            for key in set(row) & DATES:
                if row[key]:
                    row[key] = (datetime.fromisoformat(row[key]) + delta).isoformat()
        group["reference_time"] = at.isoformat()
    group["validation"] = reports
    previous = json.loads((SAMPLE / "previous-night.json").read_text())
    if at is not None:
        for row in previous["leads"] + previous["inventory"]:
            for key in set(row) & DATES:
                if row.get(key):
                    row[key] = (datetime.fromisoformat(row[key]) + delta).isoformat()
        previous["reference_time"] = (at - timedelta(days=1)).isoformat()
    group["previous"] = previous
    return group
