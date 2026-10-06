from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ChatE2ETest(unittest.TestCase):
    def test_chat_returns_initial_and_final_metrics_without_exposing_sensitive_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/jarvis_chat.py"), "analisar arquitetura", "--allow-rag-bypass", "teste supervisionado", "--database", str(Path(temporary) / "missing.db")],
                cwd=ROOT, text=True, capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["metrics"]["initial"]["phase"], "INITIAL")
        self.assertEqual(payload["metrics"]["final"]["phase"], "FINAL")
        self.assertEqual(payload["metrics"]["initial"]["rag"]["data_quality"], "RAG_BYPASS_AUTHORIZED")
        self.assertIn("Métricas iniciais", result.stderr)
        self.assertIn("Métricas finais", result.stderr)
        self.assertNotIn("teste supervisionado", result.stdout)


if __name__ == "__main__":
    unittest.main()
