import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.codex_api import CodexApiError, resolve_model, stream_response


class FakeResponse:
    def __init__(self, events):
        self.events = [f"data: {json.dumps(event)}\n\n".encode() for event in events]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        return iter(self.events)


class CodexApiTests(unittest.TestCase):
    def test_resolves_policy_model_without_frontend_override(self):
        resolved = resolve_model("gpt-5.6-terra", "medium", "MEDIUM")
        self.assertEqual(resolved["model_requested"], "gpt-5.6-terra")
        self.assertEqual(resolved["model_effective"], "gpt-5.6-terra")
        self.assertEqual(resolved["registry_version"], "1.0.0")

    def test_rejects_unknown_or_incompatible_model(self):
        with self.assertRaisesRegex(CodexApiError, "registry"):
            resolve_model("gpt-unknown", "medium", "MEDIUM")
        with self.assertRaisesRegex(CodexApiError, "incompatível"):
            resolve_model("gpt-5.6-terra", "high", "LARGE")

    def test_rejects_invalid_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(CodexApiError, "registry"):
                resolve_model("gpt-5.6-terra", "medium", "MEDIUM", path)

    def test_missing_key_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(CodexApiError, "credencial"):
                list(stream_response("oi", model="gpt-5.6-terra", reasoning="medium"))

    def test_stream_yields_only_safe_text_events(self):
        captured = {}

        def opener(request, timeout):
            captured["body"] = json.loads(request.data)
            captured["auth"] = request.headers["Authorization"]
            return FakeResponse([
                {"type": "response.output_text.delta", "delta": "Olá"},
                {"type": "response.output_text.delta", "delta": "!"},
                {"type": "response.completed", "response": {"usage": {"input_tokens": 2}}},
            ])

        events = list(stream_response("oi", model="gpt-5.6-terra", reasoning="medium", api_key="secret", opener=opener))
        self.assertEqual([event["delta"] for event in events if event["event"] == "message.delta"], ["Olá", "!"])
        self.assertEqual(events[-1]["usage"]["input_tokens"], 2)
        self.assertEqual(captured["auth"], "Bearer secret")
        self.assertEqual(captured["body"]["model"], "gpt-5.6-terra")
        self.assertFalse(captured["body"]["store"])
        self.assertNotIn("secret", json.dumps(events))


if __name__ == "__main__":
    unittest.main()
