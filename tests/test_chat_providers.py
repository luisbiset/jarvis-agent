import json
import os
import unittest
from unittest.mock import patch

from scripts.chat_providers import is_contaminated_response, provider_name, stream_cli_response
from scripts.codex_api import CodexApiError


class FakeProcess:
    returncode = 0

    def communicate(self, timeout=None):
        return ("\n".join([
            json.dumps({"type": "message.delta", "delta": "Olá"}),
            json.dumps({"type": "turn.completed", "usage": {"output_tokens": 1}}),
        ]), "")

    def kill(self):
        pass


class ChatProviderTests(unittest.TestCase):
    def test_contamination_markers_are_rejected(self):
        self.assertTrue(is_contaminated_response("Pré-métricas: complexidade baixa"))
        self.assertTrue(is_contaminated_response("[JARVIS] acionado"))
        self.assertFalse(is_contaminated_response("Análise concluída com risco baixo."))

    def test_cli_rejects_contaminated_agent_message(self):
        def runner(command, **kwargs):
            process = FakeProcess()
            process.communicate = lambda timeout=None: (json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "[JARVIS] acionado"}}), "")
            return process
        with self.assertRaisesRegex(CodexApiError, "inválida"):
            list(stream_cli_response("oi", model="gpt-5.6-terra", reasoning="medium", executable="codex", runner=runner))

    def test_provider_defaults_to_api_and_rejects_unknown(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(provider_name(), "api")
        with patch.dict(os.environ, {"CODEX_PROVIDER": "other"}):
            with self.assertRaisesRegex(CodexApiError, "provider"):
                provider_name()

    def test_cli_uses_read_only_json_and_emits_common_events(self):
        captured = {}

        def runner(command, **kwargs):
            captured["command"] = command
            captured["kwargs"] = kwargs
            return FakeProcess()

        events = list(stream_cli_response("oi", model="gpt-5.6-terra", reasoning="medium", executable="codex", runner=runner))
        self.assertEqual([event["event"] for event in events], ["provider.started", "message.delta", "provider.completed"])
        self.assertIn("--ephemeral", captured["command"])
        self.assertIn("read-only", captured["command"])
        self.assertIn("--json", captured["command"])
        self.assertIn("--ignore-user-config", captured["command"])
        self.assertIn("--ignore-rules", captured["command"])
        self.assertEqual(captured["kwargs"]["env"] if "env" in captured["kwargs"] else None, None)
        self.assertEqual(events[0]["provider"], "cli")
        self.assertNotIn("oi", json.dumps(events))

    def test_cli_converts_item_completed_agent_message(self):
        def runner(command, **kwargs):
            process = FakeProcess()
            process.communicate = lambda timeout=None: ("\n".join([
                json.dumps({"type": "item.completed", "item": {"type": "error", "message": "warning"}}),
                json.dumps({"type": "thread.started", "thread_id": "safe-id"}),
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "OK"}}),
                json.dumps({"type": "turn.completed", "usage": {"output_tokens": 1}}),
            ]), "")
            return process

        events = list(stream_cli_response("oi", model="gpt-5.6-terra", reasoning="medium", executable="codex", runner=runner))
        self.assertEqual([event.get("delta") for event in events if event["event"] == "message.delta"], ["OK"])

    def test_cli_converts_nested_agent_message_content(self):
        def runner(command, **kwargs):
            process = FakeProcess()
            process.communicate = lambda timeout=None: ("\n".join([
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "content": [{"type": "output_text", "text": "Resposta "}, {"text": "valida"}]}}),
                json.dumps({"type": "turn.completed"}),
            ]), "")
            return process
        events = list(stream_cli_response("oi", model="gpt-5.6-terra", reasoning="medium", executable="codex", runner=runner))
        self.assertEqual([event.get("delta") for event in events if event["event"] == "message.delta"], ["Resposta valida"])

    def test_cli_missing_executable_is_explicit(self):
        with patch("scripts.chat_providers._cli_command", return_value=None):
            with self.assertRaisesRegex(CodexApiError, "CLI"):
                list(stream_cli_response("oi", model="m", reasoning="low"))


if __name__ == "__main__":
    unittest.main()
