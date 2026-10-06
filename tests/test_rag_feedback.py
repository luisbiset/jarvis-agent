from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aghuse_rag_feedback.py"


class RagFeedbackTest(unittest.TestCase):
    def run_cli(self, file: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), "--file", str(file), *args], cwd=ROOT, text=True, capture_output=True)

    def test_add_without_decision_stays_pending_and_export_rejects_invalid(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "feedback.jsonl"
            created = self.run_cli(file, "add", "--query", "corrigir DAO", "--path", "scripts/x.py", "--layer", "backend", "--artifact", "code")
            self.assertEqual(created.returncode, 0, created.stderr)
            rows = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]
            self.assertIsNone(rows[0]["relevant"])
            exported = self.run_cli(file, "export", "--output", str(Path(temporary) / "dataset.jsonl"))
            self.assertEqual(exported.returncode, 0, exported.stderr)
            self.assertIn('"approved": 0', exported.stdout)

    def test_approval_requires_pending_and_preserves_false_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "feedback.jsonl"
            created = self.run_cli(file, "add", "--query", "corrigir DAO", "--path", "scripts/x.py", "--layer", "backend", "--artifact", "code")
            item_id = created.stdout.strip()
            approved = self.run_cli(file, "approve", "--id", item_id, "--irrelevant")
            self.assertEqual(approved.returncode, 0, approved.stderr)
            row = json.loads(file.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["status"], "APPROVED")
            self.assertIs(row["relevant"], False)
            repeated = self.run_cli(file, "approve", "--id", item_id, "--relevant")
            self.assertNotEqual(repeated.returncode, 0)


if __name__ == "__main__":
    unittest.main()
