import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SimulationTests(unittest.TestCase):
    def test_simulation_is_read_only_and_selects_policy(self):
        result = subprocess.run(
            [sys.executable, "scripts/jarvis_simulate.py", "--task-id", "TEST-SIM", "--task-type", "SECURITY", "--security-sensitive"],
            cwd=ROOT, text=True, capture_output=True, check=True,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(payload["simulation"])
        self.assertEqual(payload["operational_mode"], "READ_ONLY_AUDIT")
        self.assertEqual(payload["external_actions"], "blocked")
        self.assertEqual(payload["writes_performed"], 0)
        self.assertEqual(payload["reasoning"]["level"], "INSTANT")


if __name__ == "__main__":
    unittest.main()
