"""Vultr-only live transport, bounded wire protocol, and pessimistic request accounting.

No SDK, redirects, proxy environment, automatic retry, or provider fallback. The
killable controller transport process enforces a total deadline even during DNS,
TLS, slow headers or a trickling body. It never executes generated code.

Transport, usage accounting and budgets are shared by every contract. Response
content is handed to exactly one contract validator (Python source, research JSON
or outreach JSON); a rejection produces a bounded diagnostic naming the stage and
field, never the rejected text or a credential.
"""

import fcntl
import http.client
import json
import multiprocessing
import os
import re
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Protocol

from ..execution.artifacts import Rejected, sha256, strict_json
from ..execution.controller import atomic_json, now
from ..execution.runner import RunError
from ..sales.contracts import (
    ContractError,
    classify_head,
    diagnostic,
    observed_type,
    source_contract,
)

ENDPOINT = "https://api.vultrinference.com/v1/chat/completions"
MAX_PLAN_REQUESTS = 6
MAX_PLAN_TOKENS = 131072
MAX_ENVELOPE_REQUESTS = 64
MAX_ENVELOPE_TOKENS = 1048576
FINISH_REASONS = frozenset({"stop", "length", "tool_calls", "content_filter", "error"})


@dataclass(frozen=True)
class ModelConfig:
    model: str
    deadline_seconds: int = 30
    max_input_tokens: int = 12000
    max_output_tokens: int = 2048
    max_response_bytes: int = 65536

    def __post_init__(self):
        if not isinstance(self.model, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,199}", self.model
        ):
            raise RunError("invalid_model_configuration")
        bounds = {
            "deadline_seconds": (1, 60),
            "max_input_tokens": (256, 32768),
            "max_output_tokens": (1, 4096),
            "max_response_bytes": (1024, 131072),
        }
        for key, (low, high) in bounds.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise RunError("invalid_model_configuration")


class Budget:
    def __init__(
        self,
        *,
        max_requests=2,
        max_total_tokens=28096,
        ceiling_usd="0",
        input_usd_per_million="0",
        output_usd_per_million="0",
    ):
        try:
            if any(
                not isinstance(v, str) or not re.fullmatch(r"[0-9]{1,7}(?:\.[0-9]{1,12})?", v)
                for v in (ceiling_usd, input_usd_per_million, output_usd_per_million)
            ):
                raise ValueError
            self.ceiling = Decimal(ceiling_usd)
            self.input_rate = Decimal(input_usd_per_million)
            self.output_rate = Decimal(output_usd_per_million)
            values = (self.ceiling, self.input_rate, self.output_rate)
            if any(not v.is_finite() or v < 0 or v > 1000000 for v in values):
                raise ValueError
            if type(max_requests) is not int or not 1 <= max_requests <= MAX_PLAN_REQUESTS:
                raise ValueError
            if type(max_total_tokens) is not int or not 1 <= max_total_tokens <= MAX_PLAN_TOKENS:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise RunError("invalid_budget") from exc
        self.max_requests = max_requests
        self.max_total_tokens = max_total_tokens
        self.requests = 0
        self.tokens = 0
        self.cost = Decimal(0)
        self._ledger_path = None
        self.envelope = None  # Optional aggregate authorization shared by several plans.

    def bind(self, path):
        """Caller holds the checkout lock. Reopening an approval never resets spend."""
        if self._ledger_path is not None and self._ledger_path != path:
            raise RunError("model_budget_ledger_mismatch")
        policy = self.record()
        if path.exists():
            try:
                with path.open("rb") as stream:
                    raw = stream.read(8193)
                if len(raw) > 8192:
                    raise ValueError
                saved = strict_json(raw)
                counters = {"reserved_requests", "reserved_tokens", "reserved_usd"}
                if set(saved) != set(policy) or any(
                    saved[k] != policy[k] for k in policy.keys() - counters
                ):
                    raise ValueError
                requests, tokens = saved["reserved_requests"], saved["reserved_tokens"]
                cost = Decimal(saved["reserved_usd"])
                if (
                    type(requests) is not int
                    or not self.requests <= requests <= self.max_requests
                    or type(tokens) is not int
                    or not self.tokens <= tokens <= self.max_total_tokens
                    or not cost.is_finite()
                    or not self.cost <= cost <= self.ceiling
                ):
                    raise ValueError
                self.requests, self.tokens, self.cost = requests, tokens, cost
            except (OSError, ValueError, TypeError, InvalidOperation) as exc:
                raise RunError("model_budget_ledger_invalid") from exc
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._ledger_path = path
        atomic_json(path, self.record())

    def remaining_requests(self):
        return self.max_requests - self.requests

    def reserve(self, config):
        tokens = config.max_input_tokens + config.max_output_tokens
        cost = (
            config.max_input_tokens * self.input_rate + config.max_output_tokens * self.output_rate
        ) / Decimal(1000000)
        if (
            self.requests >= self.max_requests
            or self.tokens + tokens > self.max_total_tokens
            or self.cost + cost > self.ceiling
        ):
            raise RunError("model_budget_exhausted")
        if self.envelope is not None:
            # The aggregate ledger is checked and written first, so a crash between the
            # two writes can only over-count, never free capacity.
            self.envelope.reserve(tokens, cost)
        # Never refund uncertain/failed calls. A correction is another reservation.
        self.requests += 1
        self.tokens += tokens
        self.cost += cost
        if self._ledger_path is not None:
            # Durable before dispatch; even a crash before request evidence is
            # finalized cannot restore the approved allowance on a later run.
            atomic_json(self._ledger_path, self.record())
        return {
            "input_tokens": config.max_input_tokens,
            "output_tokens": config.max_output_tokens,
            "usd": str(cost),
        }

    def record(self):
        return {
            "max_requests": self.max_requests,
            "max_total_tokens": self.max_total_tokens,
            "ceiling_usd": str(self.ceiling),
            "input_usd_per_million": str(self.input_rate),
            "output_usd_per_million": str(self.output_rate),
            "reserved_requests": self.requests,
            "reserved_tokens": self.tokens,
            "reserved_usd": str(self.cost),
        }


class Envelope:
    """Aggregate authorization shared by several bounded plans (batches).

    Its durable ledger sums every reservation made under any plan that names it. The
    ledger is keyed by the envelope reference and bounds, not by a plan's config, so
    changing a plan's model settings or budget cannot open new capacity. Reopening never
    resets counters; failures never refund.
    """

    def __init__(self, *, reference, max_requests, max_total_tokens, ceiling_usd):
        try:
            if not isinstance(reference, str) or not 1 <= len(reference) <= 200:
                raise ValueError
            if type(max_requests) is not int or not 1 <= max_requests <= MAX_ENVELOPE_REQUESTS:
                raise ValueError
            if type(max_total_tokens) is not int:
                raise ValueError
            if not 1 <= max_total_tokens <= MAX_ENVELOPE_TOKENS:
                raise ValueError
            if not isinstance(ceiling_usd, str) or not re.fullmatch(
                r"[0-9]{1,7}(?:\.[0-9]{1,12})?", ceiling_usd
            ):
                raise ValueError
            self.ceiling = Decimal(ceiling_usd)
            if not self.ceiling.is_finite() or not 0 < self.ceiling <= 1000000:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise RunError("invalid_envelope") from exc
        self.reference = reference
        self.max_requests = max_requests
        self.max_total_tokens = max_total_tokens
        self.requests = 0
        self.tokens = 0
        self.cost = Decimal(0)
        self._ledger_path = None

    def policy(self):
        return {
            "reference": self.reference,
            "max_requests": self.max_requests,
            "max_total_tokens": self.max_total_tokens,
            "ceiling_usd": str(self.ceiling),
        }

    def record(self):
        return {
            **self.policy(),
            "reserved_requests": self.requests,
            "reserved_tokens": self.tokens,
            "reserved_usd": str(self.cost),
        }

    def identity(self):
        return sha256(json.dumps(self.policy(), sort_keys=True).encode())

    def _load(self, path):
        with path.open("rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            raise ValueError
        saved = strict_json(raw)
        policy = self.policy()
        if set(saved) != set(self.record()) or any(saved[k] != policy[k] for k in policy):
            raise ValueError
        requests, tokens = saved["reserved_requests"], saved["reserved_tokens"]
        cost = Decimal(saved["reserved_usd"])
        if (
            type(requests) is not int
            or not self.requests <= requests <= self.max_requests
            or type(tokens) is not int
            or not self.tokens <= tokens <= self.max_total_tokens
            or not cost.is_finite()
            or not self.cost <= cost <= self.ceiling
        ):
            raise ValueError
        self.requests, self.tokens, self.cost = requests, tokens, cost

    def bind(self, directory):
        """Open or create the aggregate ledger; reopening never resets counters."""
        path = Path(directory) / ("envelope-" + self.identity() + ".json")
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (path.parent / (path.name + ".lock")).open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if path.exists():
                    self._load(path)
                else:
                    atomic_json(path, self.record())
        except (OSError, ValueError, TypeError, InvalidOperation) as exc:
            raise RunError("model_envelope_ledger_invalid") from exc
        self._ledger_path = path
        return self.identity()

    def reserve(self, tokens, cost):
        """Re-read the shared ledger under its lock, then reserve or refuse."""
        if self._ledger_path is None:
            raise RunError("model_envelope_unbound")
        with (self._ledger_path.parent / (self._ledger_path.name + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                self._load(self._ledger_path)
            except (OSError, ValueError, TypeError, InvalidOperation) as exc:
                raise RunError("model_envelope_ledger_invalid") from exc
            if (
                self.requests >= self.max_requests
                or self.tokens + tokens > self.max_total_tokens
                or self.cost + cost > self.ceiling
            ):
                raise RunError("model_envelope_exhausted")
            self.requests += 1
            self.tokens += tokens
            self.cost += cost
            atomic_json(self._ledger_path, self.record())


@dataclass(frozen=True)
class Authorization:
    """Operator-supplied approval of one exact plan; never created by a model."""

    config: ModelConfig
    budget: Budget
    approval_reference: str
    pricing_source: str
    pricing_checked_at: str
    envelope: Envelope | None = None

    @classmethod
    def load(cls, path: Path):
        try:
            with path.open("rb") as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError
            data = strict_json(raw)
            keys = {
                "config",
                "budget",
                "approval_reference",
                "pricing_source",
                "pricing_checked_at",
            }
            if set(data) not in (keys, keys | {"envelope"}):
                raise ValueError
            envelope = None
            if "envelope" in data:
                if not isinstance(data["envelope"], dict) or set(data["envelope"]) != {
                    "reference",
                    "max_requests",
                    "max_total_tokens",
                    "ceiling_usd",
                }:
                    raise ValueError
                envelope = Envelope(**data["envelope"])
            if set(data["config"]) != set(asdict(ModelConfig("schema-check"))) or set(
                data["budget"]
            ) != {
                "max_requests",
                "max_total_tokens",
                "ceiling_usd",
                "input_usd_per_million",
                "output_usd_per_million",
            }:
                raise ValueError
            auth = cls(
                ModelConfig(**data["config"]),
                Budget(**data["budget"]),
                data["approval_reference"],
                data["pricing_source"],
                data["pricing_checked_at"],
                envelope,
            )
            if (
                not isinstance(auth.approval_reference, str)
                or not 1 <= len(auth.approval_reference) <= 200
                or not re.fullmatch(
                    r"https://(?:(?:docs\.|www\.)?vultr\.com|api\.vultrinference\.com)/[^\s]{1,300}",
                    auth.pricing_source,
                )
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", auth.pricing_checked_at)
                or auth.budget.ceiling <= 0
                or auth.budget.input_rate <= 0
                or auth.budget.output_rate <= 0
            ):
                raise ValueError
            return auth
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise RunError("invalid_live_authorization") from exc

    def record(self):
        return {
            "approval_reference": self.approval_reference,
            "pricing_source": self.pricing_source,
            "pricing_checked_at": self.pricing_checked_at,
            "envelope": self.envelope.policy() if self.envelope else None,
        }

    def bind_budget(self, directory):
        policy = self.budget.record()
        for key in ("reserved_requests", "reserved_tokens", "reserved_usd"):
            policy.pop(key)
        identity = sha256(
            json.dumps(
                {"config": asdict(self.config), "budget": policy, **self.record()}, sort_keys=True
            ).encode()
        )
        if self.envelope is not None:
            # Bind the aggregate first: a plan never reserves outside its envelope.
            self.envelope.bind(directory)
            self.budget.envelope = self.envelope
        self.budget.bind(directory / (identity + ".json"))
        return identity


@dataclass(frozen=True)
class WireResponse:
    status: int
    body: bytes


def validate_reasoning(option, config):
    """Documented request shapes only: disabled, or a bounded minimal/low effort."""
    if option is None:
        return
    try:
        if set(option) == {"enabled"} and option["enabled"] is False:
            return
        if (
            set(option) == {"effort", "max_tokens"}
            and option["effort"] in ("minimal", "low")
            and type(option["max_tokens"]) is int
            and 1 <= option["max_tokens"] < config.max_output_tokens
        ):
            return
    except (TypeError, AttributeError):
        pass
    raise RunError("invalid_request_controls")


def validate_response_format(option):
    if option is None:
        return
    if (
        not isinstance(option, dict)
        or set(option) != {"type"}
        or option["type"]
        not in (
            "text",
            "json_object",
        )
    ):
        raise RunError("invalid_request_controls")


def load_request_controls(path):
    """Separately approved restrictive follow-up; never changes the spend identity."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            raise ValueError
        controls = strict_json(raw)
        if set(controls) != {
            "approval_reference",
            "parent_approval_reference",
            "model",
            "reasoning",
        }:
            raise ValueError
        return controls
    except (OSError, ValueError, TypeError) as exc:
        raise RunError("invalid_request_controls") from exc


def validate_request_controls(controls, provider, config):
    if controls is None:
        return
    try:
        auth = provider.authorization
        if (
            provider.kind != "vultr_serverless_inference"
            or controls["parent_approval_reference"] != auth.approval_reference
            or controls["model"] != config.model
            or not isinstance(controls["approval_reference"], str)
            or not 1 <= len(controls["approval_reference"]) <= 200
        ):
            raise ValueError
        validate_reasoning(controls["reasoning"], config)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise RunError("invalid_request_controls") from exc


def _http_worker(pipe, key, payload, config):
    connection = None
    try:
        connection = http.client.HTTPSConnection(
            "api.vultrinference.com", timeout=config.deadline_seconds
        )
        connection.request(
            "POST",
            "/v1/chat/completions",
            body=payload,
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
        )
        response = connection.getresponse()
        # Never follow redirects or save provider diagnostics/error bodies.
        if response.status != 200:
            pipe.send(("http", response.status, b""))
            return
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            pipe.send(("error", "provider_encoding_rejected", b""))
            return
        declared = response.getheader("Content-Length")
        if declared is not None and (
            not declared.isdecimal() or int(declared) > config.max_response_bytes
        ):
            pipe.send(("error", "provider_response_limit", b""))
            return
        body = response.read(config.max_response_bytes + 1)
        if len(body) > config.max_response_bytes:
            pipe.send(("error", "provider_response_limit", b""))
        else:
            pipe.send(("http", response.status, body))
    except Exception:
        pipe.send(("error", "provider_transport_error", b""))
    finally:
        if connection is not None:
            connection.close()
        pipe.close()


def vultr_transport(key, payload, config, *, worker=_http_worker):
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(sender, key, payload, config), daemon=True)
    deadline = time.monotonic() + config.deadline_seconds
    try:
        process.start()
        sender.close()
        if not receiver.poll(max(0, deadline - time.monotonic())):
            raise RunError("provider_deadline_exceeded")
        try:
            kind, value, body = receiver.recv()
        except EOFError as exc:
            raise RunError("provider_transport_error") from exc
        if kind == "error":
            raise RunError(value)
        return WireResponse(value, body)
    finally:
        receiver.close()
        sender.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
                if process.is_alive():
                    raise RunError("provider_transport_cleanup_failed")
            process.close()


class Provider(Protocol):
    kind: str

    def ready(self, config: ModelConfig, budget: Budget): ...
    def request(self, payload: bytes, config: ModelConfig) -> WireResponse: ...


class VultrProvider:
    kind = "vultr_serverless_inference"

    def __init__(self, authorization=None, *, key=None, transport=vultr_transport):
        self.authorization = authorization
        self._key = key
        self._transport = transport

    def ready(self, config, budget):
        if not (self._key or os.environ.get("VULTR_INFERENCE_API_KEY")):
            raise RunError("missing_vultr_credentials")
        if (
            self.authorization is None
            or self.authorization.config != config
            or self.authorization.budget is not budget
        ):
            raise RunError("live_spending_not_authorized")
        if os.environ.get("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1") != (
            "https://api.vultrinference.com/v1"
        ):
            raise RunError("vultr_endpoint_override_rejected")

    def request(self, payload, config):
        return self._transport(self._key or os.environ["VULTR_INFERENCE_API_KEY"], payload, config)


class FakeProvider:
    """Labelled original fixture responses; no network or model inference."""

    kind = "offline_fake_provider"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def ready(self, config, budget):
        pass

    def request(self, payload, config):
        self.requests.append(payload)
        try:
            response = next(self.responses)
        except StopIteration as exc:
            raise RunError("fake_responses_exhausted") from exc
        if isinstance(response, BaseException):
            raise response
        return response


class ReplayProvider:
    """Replays a previously accepted live response for the identical request bytes.

    No network, no charge. Only responses the controller accepted and saved are
    served, keyed by request hash, so a replay can never introduce new content.
    """

    kind = "saved_replay"

    def __init__(self, directory):
        self.directory = Path(directory)
        self.requests = []

    def ready(self, config, budget):
        pass

    def request(self, payload, config):
        self.requests.append(payload)
        path = self.directory / (sha256(payload) + ".json")
        if path.is_symlink() or not path.is_file():
            raise RunError("replay_not_available")
        with path.open("rb") as stream:
            body = stream.read(config.max_response_bytes + 1)
        return WireResponse(200, body)


def fake_response(content, model="offline-extraction-fixture", **extra):
    if isinstance(content, bytes):
        content = content.decode()
    message = {"role": "assistant", "content": content}
    message.update(extra.pop("message", {}))
    body = {
        "id": "offline-fixture-response",
        "model": model,
        "choices": [{"finish_reason": "stop", "message": message}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600},
    }
    body.update(extra)
    return WireResponse(200, json.dumps(body).encode())


USAGE_KINDS = {
    "offline_fake_provider": "synthetic",
    "saved_replay": "replayed_provider_usage",
    "vultr_serverless_inference": "provider_reported",
}


def _malformed(stage, field, **extra):
    raise ContractError("provider_malformed_response", diagnostic(stage, field, **extra))


def _parse_envelope(body, config, receipt):
    """Protocol checks shared by every contract. Returns assistant content text."""
    try:
        data = strict_json(body)
    except (ValueError, Rejected, RecursionError) as exc:
        _malformed(
            "envelope",
            "$",
            expected="json_object",
            observed="unparseable",
            detail=exc.args[0] if isinstance(exc, Rejected) else "json_decode_error",
        )
    if not isinstance(data, dict):
        _malformed("envelope", "$", expected="object", observed=observed_type(data))
    receipt["response_keys"] = sorted(str(k)[:40] for k in data)[:20]
    usage = data.get("usage")
    if not isinstance(usage, dict):
        _malformed("usage", "usage", expected="object", observed=observed_type(usage))
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if type(usage.get(key)) is not int or usage[key] < 0:
            _malformed(
                "usage",
                f"usage.{key}",
                expected="non-negative int",
                observed=observed_type(usage.get(key)),
            )
    receipt["usage"] = {k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    details = usage.get("completion_tokens_details")
    if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int:
        receipt["reasoning_tokens"] = details["reasoning_tokens"]
    if (
        usage["prompt_tokens"] > config.max_input_tokens
        or usage["completion_tokens"] > config.max_output_tokens
        or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]
    ):
        receipt["diagnostic"] = diagnostic(
            "usage",
            "usage",
            expected="within configured caps",
            observed="limit_or_total_inconsistent",
        )
        raise RunError("provider_usage_limit")
    response_id = data.get("id")
    if not isinstance(response_id, str) or not 1 <= len(response_id) <= 200:
        _malformed("envelope", "id", expected="string", observed=observed_type(response_id))
    receipt["provider_response_id"] = response_id
    model = data.get("model")
    if not isinstance(model, str) or not 1 <= len(model) <= 200:
        _malformed("envelope", "model", expected="string", observed=observed_type(model))
    # The official contract documents that the response model "may differ from
    # request". Record the echo and whether it matched instead of rejecting it.
    receipt["response_model"] = model
    receipt["model_echo_matches"] = model == config.model
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        count = len(choices) if isinstance(choices, list) else "?"
        _malformed(
            "envelope",
            "choices",
            expected="array of exactly 1",
            observed=f"{observed_type(choices)}[{count}]",
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        _malformed("choice", "choices[0]", expected="object", observed=observed_type(choice))
    finish = choice.get("finish_reason")
    receipt["finish_reason"] = (
        finish
        if isinstance(finish, str) and finish in FINISH_REASONS
        else (observed_type(finish) if not isinstance(finish, str) else "unknown_value")
    )
    message = choice.get("message")
    if not isinstance(message, dict):
        _malformed(
            "message", "choices[0].message", expected="object", observed=observed_type(message)
        )
    reasoning = message.get("reasoning")
    receipt["reasoning_present"] = isinstance(reasoning, str) and bool(reasoning.strip())
    receipt["reasoning_chars"] = len(reasoning) if isinstance(reasoning, str) else None
    content = message.get("content")
    receipt["content_chars"] = len(content) if isinstance(content, str) else None
    if finish != "stop":
        receipt["diagnostic"] = diagnostic(
            "choice",
            "choices[0].finish_reason",
            expected="stop",
            observed=receipt["finish_reason"],
            reasoning_tokens=receipt.get("reasoning_tokens"),
            content_chars=receipt["content_chars"],
        )
        raise RunError("provider_incomplete_response")
    if message.get("tool_calls") or message.get("function_call"):
        _malformed(
            "message",
            "choices[0].message.tool_calls",
            expected="absent",
            observed="tool_call_present",
        )
    if message.get("role") != "assistant":
        _malformed(
            "message",
            "choices[0].message.role",
            expected="assistant",
            observed=observed_type(message.get("role")),
        )
    if not isinstance(content, str):
        _malformed(
            "message",
            "choices[0].message.content",
            expected="string",
            observed=observed_type(content),
            reasoning_present=receipt["reasoning_present"],
        )
    receipt["content_head"] = classify_head(content.encode("utf-8"))
    return content


def complete(
    provider,
    config,
    budget,
    messages,
    path,
    *,
    contract,
    contract_name,
    request_controls=None,
    reasoning=None,
    response_format=None,
    replay_store=None,
    prefer_replay=False,
):
    """One bounded request through one contract. Reservation persists before dispatch."""
    started = time.monotonic()
    receipt = {
        "schema_version": 2,
        "contract": contract_name,
        "started_at": now(),
        "finished_at": None,
        "provider": provider.kind,
        "config": asdict(config),
        "endpoint": ENDPOINT if provider.kind == "vultr_serverless_inference" else None,
        "status": "pending",
        "failure_reason": None,
        "diagnostic": None,
        "request_sha256": None,
        "request_options": {"reasoning": reasoning, "response_format": response_format},
        "response_sha256": None,
        "response_bytes": None,
        "response_keys": None,
        "http_status": None,
        "elapsed_seconds": None,
        "provider_response_id": None,
        "response_model": None,
        "model_echo_matches": None,
        "finish_reason": None,
        "reasoning_tokens": None,
        "reasoning_present": None,
        "reasoning_chars": None,
        "content_chars": None,
        "content_head": None,
        "usage": None,
        "usage_kind": USAGE_KINDS.get(provider.kind, "provider_reported"),
        "reservation": None,
        "budget": budget.record(),
        "envelope": budget.envelope.record() if budget.envelope else None,
        "dispatched": False,
        "request_controls": request_controls,
    }
    atomic_json(path, receipt)
    try:
        validate_request_controls(request_controls, provider, config)
        reasoning_option = request_controls["reasoning"] if request_controls else reasoning
        validate_reasoning(reasoning_option, config)
        validate_response_format(response_format)
        receipt["request_options"]["reasoning"] = reasoning_option
        request = {
            "model": config.model,
            "messages": messages,
            "max_completion_tokens": config.max_output_tokens,
            "temperature": 0,
            "stream": False,
            "n": 1,
        }
        if reasoning_option is not None:
            request["reasoning"] = reasoning_option
        if response_format is not None:
            request["response_format"] = response_format
        payload = json.dumps(request, ensure_ascii=False).encode()
        # Conservative byte-token allowance plus 256 tokens of framing. Selected
        # live model/tokenizer compatibility must be confirmed in its approved plan.
        if len(payload) + 256 > config.max_input_tokens:
            raise RunError("model_input_token_limit")
        receipt["request_sha256"] = sha256(payload)
        cached = (
            prefer_replay
            and replay_store is not None
            and (Path(replay_store) / (receipt["request_sha256"] + ".json")).is_file()
        )
        if cached:
            provider = ReplayProvider(replay_store)
            receipt["provider"] = provider.kind
            receipt["endpoint"] = None
            receipt["usage_kind"] = USAGE_KINDS[provider.kind]
        provider.ready(config, budget)
        receipt["reservation"] = None if cached else budget.reserve(config)
        receipt["budget"] = budget.record()
        receipt["envelope"] = budget.envelope.record() if budget.envelope else None
        (path.parent / "request.json").write_bytes(payload)
        receipt["dispatched"] = True
        atomic_json(path, receipt)
        response = provider.request(payload, config)
        receipt["http_status"] = response.status
        if response.status != 200:
            raise RunError(
                "provider_redirect_rejected"
                if 300 <= response.status < 400
                else "provider_http_error"
            )
        if len(response.body) > config.max_response_bytes:
            raise RunError("provider_response_limit")
        receipt["response_bytes"] = len(response.body)
        receipt["response_sha256"] = sha256(response.body)
        content = _parse_envelope(response.body, config, receipt)
        value = contract(content)
        (path.parent / "response.json").write_bytes(response.body)
        if replay_store is not None and provider.kind == "vultr_serverless_inference":
            replay_store = Path(replay_store)
            replay_store.mkdir(parents=True, exist_ok=True, mode=0o700)
            (replay_store / (receipt["request_sha256"] + ".json")).write_bytes(response.body)
        receipt["status"] = "succeeded"
        return value, receipt
    except ContractError as exc:
        receipt["status"] = "failed"
        receipt["failure_reason"] = exc.reason
        receipt["diagnostic"] = exc.diagnostic
        raise RunError(exc.reason) from None
    except RunError as exc:
        receipt["status"] = "failed"
        receipt["failure_reason"] = exc.reason
        raise
    except KeyboardInterrupt:
        receipt["status"] = "interrupted"
        receipt["failure_reason"] = "controller_interrupted"
        raise
    except Exception as exc:
        receipt["status"] = "failed"
        receipt["failure_reason"] = "provider_internal_error"
        raise RunError("provider_internal_error") from exc
    finally:
        receipt["finished_at"] = now()
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        atomic_json(path, receipt)


def generate(provider, config, budget, messages, path, *, request_controls=None, reasoning=None):
    """Executable-source contract. Accepted source is saved; rejected source never is."""
    script, receipt = complete(
        provider,
        config,
        budget,
        messages,
        path,
        contract=source_contract,
        contract_name="python_source",
        request_controls=request_controls,
        reasoning=reasoning,
    )
    (path.parent / "script.py").write_bytes(script)
    return script, receipt
