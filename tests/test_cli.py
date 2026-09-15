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


if __name__ == "__main__":
    unittest.main()
