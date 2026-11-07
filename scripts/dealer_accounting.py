"""Read-only dealer inference accounting. Never dispatches or resets a budget ledger."""

import json
from dataclasses import asdict
from decimal import Decimal

from backend.app.execution.artifacts import sha256
from backend.app.execution.controller import ROOT
from backend.app.generation.provider import Authorization


def accounting():
    requests = 0
    reserved = Decimal(0)
    unit_reservations = set()
    for path in (ROOT / ".local/dealer-plans").glob("*.json"):
        auth = Authorization.load(path)
        policy = auth.budget.record()
        for key in ("reserved_requests", "reserved_tokens", "reserved_usd"):
            policy.pop(key)
        identity = sha256(
            json.dumps(
                dict(config=asdict(auth.config), budget=policy, **auth.record()), sort_keys=True
            ).encode()
        )
        saved = json.loads((ROOT / ".local/model-budgets" / (identity + ".json")).read_text())
        requests += saved["reserved_requests"]
        reserved += Decimal(saved["reserved_usd"])
        unit_reservations.add(
            (
                auth.config.max_input_tokens * auth.budget.input_rate
                + auth.config.max_output_tokens * auth.budget.output_rate
            )
            / Decimal(1000000)
        )
    responses = []
    for path in (ROOT / ".local/replays").glob("*.json"):
        value = json.loads(path.read_text())
        try:
            content = json.loads(value["choices"][0]["message"]["content"])
        except (KeyError, ValueError, TypeError):
            continue
        if isinstance(content, dict) and set(content) in (
            {"headline", "findings", "follow_ups"},
            {"headline", "findings", "recommendations"},
        ):
            responses.append(value)
    known = sum(
        (
            (
                Decimal(v["usage"]["prompt_tokens"]) * Decimal(".10")
                + Decimal(v["usage"]["completion_tokens"]) * Decimal(".20")
            )
            / Decimal(1000000)
            for v in responses
        ),
        start=Decimal(0),
    )
    unknown = max(0, requests - len(responses))
    uncertain = unknown * max(unit_reservations, default=Decimal(0))
    return dict(
        live_requests=requests,
        accepted_unique_responses=len(responses),
        rejected_or_uncertain_requests=unknown,
        accepted_usage_estimate_usd=str(known),
        uncertain_pessimistic_allowance_usd=str(uncertain),
        known_plus_uncertain_estimate_usd=str(known + uncertain),
        pessimistic_reserved_usd=str(reserved),
        note="Dealer envelope only; provider token estimates, not compute billing receipts.",
    )


if __name__ == "__main__":
    print(json.dumps(accounting(), indent=2))
