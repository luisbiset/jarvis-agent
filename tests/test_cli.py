import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class JarvisCliTests(unittest.TestCase):
    def test_simulate_dispatch(self):
        result = subprocess.run(
            [sys.executable, "scripts/jarvis.py", "simular", "--task-id", "CLI-TEST"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertTrue(json.loads(result.stdout)["simulation"])

    def test_git_summary_dispatch(self):
        result = subprocess.run(
            [sys.executable, "scripts/jarvis.py", "resumo-git"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertIn("branch", json.loads(result.stdout))

    def test_chat_dispatch_runs_rag_before_planning(self):
        result = subprocess.run(
            [sys.executable, "scripts/jarvis.py", "chat", "corrigir regra ContaON no AGHUse", "--context-budget", "SMALL"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stage"], "RAG_BEFORE_PLANNING")
        self.assertTrue(payload["rag"]["retrieved"])

    def test_chat_dispatch_bypasses_general_message(self):
        result = subprocess.run(
            [sys.executable, "scripts/jarvis.py", "chat", "qual a hora agora"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        self.assertFalse(json.loads(result.stdout)["rag"]["retrieved"])


if __name__ == "__main__":
    unittest.main()
