"""Two bounded analyst contracts. Model quantities and vehicle facts use field references.

Lexical grounding is deliberately restrictive for customer-facing drafts. Accepted prose
uses an allowlist; all vehicle, store, price, age, trade and name facts are controller
placeholders. This is a drafting contract, not a factual guarantee; people approve.
"""

import re

from ..sales.contracts import NUMBER_WORDS, QUANTIFIERS, ContractError, diagnostic, json_object

PLACEHOLDER = re.compile(r"\[(metric|field):([a-zA-Z0-9_.-]+)\]")
FORBIDDEN = re.compile(
    r"\b(send|sent|sending|dispatch|delivered|guarantee\w*|roi|discount\w*|"
    r"promise\w*|savings?|profit\w*|will (?:increase|sell|boost)|"
    r"reserved|reservation|financing|approved credit)\b",
    re.I,
)
MESSAGE_WORDS = set(
    """hi hello i we you your our a an the this that it is are have has found
at in on for with and or of to from as about be would could can may like look take see
review interested interest option alternative match matches similar currently listed price
available stock store vehicle car still discuss explore visit appointment arrange
trade also happy help thanks thank let me know if please salesperson regards best
follow up checking wanted asked wanted considering new another morning good subject
silver blue white black red gray SUV sedan truck wagon hybrid""".lower().split()
)
# Vehicle colors/body names are facts too: require placeholders for these.
MESSAGE_WORDS -= set("silver blue white black red gray suv sedan truck wagon hybrid".split())


def reject(kind, field, reason):
    raise ContractError(kind + "_contract_rejected", diagnostic("contract", field, observed=reason))


def fields_for(lead, unit):
    wanted = lead["wanted"]

    def vehicle(u):
        return " ".join(str(u[k]) for k in ("year", "make", "model", "trim") if u.get(k))

    trade = lead["trade_in"].split("|")
    return dict(
        first_name=lead["first_name"],
        vehicle=vehicle(unit),
        color=unit["color"],
        model=unit["model"],
        trim=unit["trim"],
        year=str(unit["year"]),
        price=f"${unit['list_price']:,.0f}",
        days_on_lot=str(unit["days_on_lot"]),
        store=unit["store_name"],
        trade_in=" ".join(trade[:3]) if trade else "",
        desired_vehicle=vehicle(wanted),
        desired_color=wanted.get("color", ""),
    )


def metric_fields(result, group):
    metrics = result.get("metrics", result.get("totals", {}))
    fields = {
        key: (
            f"${value:,.0f}"
            if key in ("recoverable_gross", "floorplan_daily", "floorplan_to_date")
            else str(value)
        )
        for key, value in metrics.items()
        if value is not None
    }
    fields["group"] = group["group"]
    roofs = {r["id"]: r for r in group["rooftops"]}
    if result.get("rooftop_id"):
        fields["store"] = roofs[result["rooftop_id"]]["name"]
    for roof in result.get("rooftops", []):
        fields["store." + roof["rooftop_id"]] = roofs[roof["rooftop_id"]]["name"]
        fields["response." + roof["rooftop_id"]] = str(roof["median_response_minutes"])
    for ix, source in enumerate(result.get("sources", [])):
        fields[f"source.{ix}"] = source["source"]
        fields[f"close_rate.{ix}"] = f"{source['close_rate'] * 100:.1f}%"
    return fields


def render(text, metrics, fields=None):
    fields = fields or {}
    return PLACEHOLDER.sub(lambda m: (metrics if m[1] == "metric" else fields)[m[2]], text)


def prose(text, kind, path, metrics, fields=None, *, message=False, maximum=240):
    if not isinstance(text, str) or not 1 <= len(text) <= 1200:
        reject(kind, path, "invalid_string")
    fields = fields or {}
    for m in PLACEHOLDER.finditer(text):
        if m[2] not in (metrics if m[1] == "metric" else fields):
            reject(kind, path, "unknown_reference")
    stripped = PLACEHOLDER.sub(" ", text).replace("[Salesperson]", " ")
    if "[" in stripped or "]" in stripped:
        reject(kind, path, "malformed_reference")
    if re.search(r"[0-9%$€£]", stripped):
        reject(kind, path, "literal_quantity")
    if any(
        re.search(r"\b" + word + r"\b", stripped, re.I)
        for word in set(NUMBER_WORDS) | set(QUANTIFIERS)
    ):
        reject(kind, path, "written_quantity")
    if FORBIDDEN.search(stripped):
        reject(kind, path, "unsupported_promise_or_send")
    if message:
        words = set(re.findall(r"[a-z]+", stripped.lower()))
        if words - MESSAGE_WORDS:
            reject(kind, path, "draft_ungrounded_words")
        # Drafts can only use contextual fields, so another lead's metrics cannot leak in.
        if any(m[1] == "metric" for m in PLACEHOLDER.finditer(text)):
            reject(kind, path, "draft_metric_reference")
    rendered = render(text, metrics, fields)
    if len(rendered) > maximum:
        reject(kind, path, "rendered_length")
    return text


def validate(content, kind, result, group):
    data = json_object(content, kind)
    required = (
        {"headline", "findings", "follow_ups"}
        if kind == "rooftop_brief"
        else {"headline", "findings", "recommendations"}
    )
    if set(data) != required:
        reject(kind, "$", "keys_mismatch")
    metrics = metric_fields(result, group)
    data["headline"] = prose(data["headline"], kind, "headline", metrics, maximum=200)
    cap = 3 if kind == "rooftop_brief" else 4
    if not isinstance(data["findings"], list) or len(data["findings"]) > cap:
        reject(kind, "findings", "list_limit")
    data["findings"] = [prose(v, kind, "findings", metrics, maximum=240) for v in data["findings"]]
    if kind == "group_brief":
        if not isinstance(data["recommendations"], list) or len(data["recommendations"]) > 3:
            reject(kind, "recommendations", "list_limit")
        data["recommendations"] = [
            prose(v, kind, "recommendations", metrics, maximum=240) for v in data["recommendations"]
        ]
    else:
        leads = {lead["lead_id"]: lead for lead in result["queue"][:3] if lead["matches"]}
        followups = data["follow_ups"]
        if not isinstance(followups, list) or len(followups) != len(leads):
            reject(kind, "follow_ups", "top_leads_required")
        seen = set()
        for row in followups:
            if not isinstance(row, dict) or set(row) != {
                "lead_id",
                "stock_no",
                "reason",
                "sms",
                "email_subject",
                "email_body",
            }:
                reject(kind, "follow_ups", "keys_mismatch")
            lid = row["lead_id"]
            if not isinstance(lid, str) or lid not in leads or lid in seen:
                reject(kind, "lead_id", "unknown_or_duplicate")
            seen.add(lid)
            lead = leads[lid]
            if row["stock_no"] != lead["matches"][0]["stock_no"]:
                reject(kind, "stock_no", "best_match_required")
            fields = fields_for(lead, lead["matches"][0])
            row["reason"] = prose(row["reason"], kind, "reason", metrics, fields, maximum=200)
            for key, limit in [("sms", 320), ("email_subject", 100), ("email_body", 700)]:
                row[key] = prose(row[key], kind, key, metrics, fields, message=True, maximum=limit)
            for key in ("sms", "email_body"):
                if "[field:first_name]" not in row[key] or "[Salesperson]" not in row[key]:
                    reject(kind, key, "name_and_signoff_required")
    return data


def rendered(reading, result, group):
    metrics = metric_fields(result, group)
    data = dict(reading)
    for key in ("headline", "findings", "recommendations"):
        if key in data:
            data[key] = (
                [render(v, metrics) for v in data[key]]
                if isinstance(data[key], list)
                else render(data[key], metrics)
            )
    if "follow_ups" in data:
        leads = {lead["lead_id"]: lead for lead in result["queue"]}
        data["follow_ups"] = [
            {
                key: (
                    render(
                        value,
                        metrics,
                        fields_for(leads[row["lead_id"]], leads[row["lead_id"]]["matches"][0]),
                    )
                    if key not in ("lead_id", "stock_no")
                    else value
                )
                for key, value in row.items()
            }
            for row in data["follow_ups"]
        ]
    return data
