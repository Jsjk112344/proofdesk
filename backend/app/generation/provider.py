"""Vultr-only live transport, bounded wire protocol, and pessimistic request accounting.

No SDK, redirects, proxy environment, automatic retry, or provider fallback. The
killable controller transport process enforces a total deadline even during DNS,
TLS, slow headers or a trickling body. It never executes generated code.
"""

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
from ..execution.controller import TASK_BYTES, atomic_json, now
from ..execution.runner import RunError

ENDPOINT = "https://api.vultrinference.com/v1/chat/completions"


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
            if type(max_requests) is not int or not 1 <= max_requests <= 2:
                raise ValueError
            if type(max_total_tokens) is not int or not 1 <= max_total_tokens <= 73728:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise RunError("invalid_budget") from exc
        self.max_requests = max_requests
        self.max_total_tokens = max_total_tokens
        self.requests = 0
        self.tokens = 0
        self.cost = Decimal(0)
        self._ledger_path = None

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


@dataclass(frozen=True)
class Authorization:
    """Operator-supplied approval of one exact plan; never created by a model."""

    config: ModelConfig
    budget: Budget
    approval_reference: str
    pricing_source: str
    pricing_checked_at: str

    @classmethod
    def load(cls, path: Path):
        try:
            with path.open("rb") as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError
            data = strict_json(raw)
            if set(data) != {
                "config",
                "budget",
                "approval_reference",
                "pricing_source",
                "pricing_checked_at",
            }:
                raise ValueError
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
        self.budget.bind(directory / (identity + ".json"))
        return identity


@dataclass(frozen=True)
class WireResponse:
    status: int
    body: bytes


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


def fake_response(script: bytes, model="offline-extraction-fixture"):
    return WireResponse(
        200,
        json.dumps(
            {
                "id": "offline-fixture-response",
                "model": model,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": script.decode()},
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 500, "total_tokens": 600},
            }
        ).encode(),
    )


def generate(provider, config, budget, messages, path):
    """Persist reservation before dispatch. Raw errors never enter records or prompts."""
    started = time.monotonic()
    receipt = {
        "schema_version": 1,
        "started_at": now(),
        "finished_at": None,
        "provider": provider.kind,
        "config": asdict(config),
        "endpoint": ENDPOINT if provider.kind == "vultr_serverless_inference" else None,
        "status": "pending",
        "failure_reason": None,
        "request_sha256": None,
        "response_sha256": None,
        "response_bytes": None,
        "http_status": None,
        "elapsed_seconds": None,
        "provider_response_id": None,
        "usage": None,
        "usage_kind": "synthetic"
        if provider.kind == "offline_fake_provider"
        else "provider_reported",
        "reservation": None,
        "budget": budget.record(),
        "dispatched": False,
    }
    atomic_json(path, receipt)
    try:
        provider.ready(config, budget)
        payload = json.dumps(
            {
                "model": config.model,
                "messages": messages,
                "max_completion_tokens": config.max_output_tokens,
                "temperature": 0,
                "stream": False,
                "n": 1,
            },
            ensure_ascii=False,
        ).encode()
        # Conservative byte-token allowance plus 256 tokens of framing. Selected
        # live model/tokenizer compatibility must be confirmed in its approved plan.
        if len(payload) + 256 > config.max_input_tokens:
            raise RunError("model_input_token_limit")
        receipt["request_sha256"] = sha256(payload)
        receipt["reservation"] = budget.reserve(config)
        receipt["budget"] = budget.record()
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
        try:
            data = strict_json(response.body)
            usage = data["usage"]
            if any(
                type(usage[k]) is not int or usage[k] < 0
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            ):
                raise ValueError
            receipt["usage"] = {
                k: usage[k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            }
            if (
                usage["prompt_tokens"] > config.max_input_tokens
                or usage["completion_tokens"] > config.max_output_tokens
                or usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]
            ):
                raise RunError("provider_usage_limit")
            response_id = data["id"]
            if not isinstance(response_id, str) or not 1 <= len(response_id) <= 200:
                raise ValueError
            receipt["provider_response_id"] = response_id
            if data["model"] != config.model or len(data["choices"]) != 1:
                raise ValueError
            choice = data["choices"][0]
            if choice["finish_reason"] != "stop":
                raise RunError("provider_incomplete_response")
            message = choice["message"]
            if message.get("tool_calls") or message.get("function_call"):
                raise ValueError
            content = message["content"]
            if message["role"] != "assistant" or not isinstance(content, str):
                raise ValueError
            script = content.encode("utf-8")
            if not script.strip() or b"\x00" in script or script.lstrip().startswith(b"```"):
                raise ValueError
            if len(script) > TASK_BYTES:
                raise RunError("generated_script_limit")
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, Rejected) as exc:
            raise RunError("provider_malformed_response") from exc
        (path.parent / "response.json").write_bytes(response.body)
        (path.parent / "script.py").write_bytes(script)
        receipt["status"] = "succeeded"
        return script, receipt
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
