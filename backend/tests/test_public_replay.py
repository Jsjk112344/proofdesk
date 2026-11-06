"""Public exact-input replay preserves contract validation without paid reservations."""

import json
import tempfile
import unittest
from pathlib import Path

from backend.app.execution.artifacts import sha256
from backend.app.generation.provider import (
    Budget,
    FakeProvider,
    ModelConfig,
    complete,
    fake_response,
)


class PublicReplayTests(unittest.TestCase):
    def test_identical_request_replays_and_changed_request_dispatches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = ModelConfig("fixture")
            messages = [{"role": "user", "content": "original"}]
            provider = FakeProvider([fake_response('{"ok": true}')])
            budget = Budget(max_requests=2, ceiling_usd="1")
            options = dict(contract=json.loads, contract_name="research", replay_store=root)
            _, first = complete(provider, config, budget, messages, root / "first.json", **options)
            payload = (root / "request.json").read_bytes()
            (root / (sha256(payload) + ".json")).write_bytes(fake_response('{"ok": true}').body)
            provider = FakeProvider([fake_response('{"ok": false}')])
            value, replay = complete(
                provider,
                config,
                budget,
                messages,
                root / "replay.json",
                prefer_replay=True,
                **options,
            )
            self.assertTrue(value["ok"])
            self.assertEqual(replay["provider"], "saved_replay")
            self.assertIsNone(replay["reservation"])
            self.assertEqual(budget.requests, 1)
            self.assertEqual(provider.requests, [])
            value, changed = complete(
                provider,
                config,
                budget,
                [{"role": "user", "content": "changed"}],
                root / "changed.json",
                prefer_replay=True,
                **options,
            )
            self.assertFalse(value["ok"])
            self.assertEqual(budget.requests, 2)
            self.assertNotEqual(first["request_sha256"], changed["request_sha256"])
