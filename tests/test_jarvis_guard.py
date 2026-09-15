import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jarvis_guard", ROOT / "scripts/jarvis_guard.py")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class JarvisGuardTests(unittest.TestCase):
    def test_audit_rejects_credentials_and_clinical_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / "sample.md").write_text("password=secret123\nprontuario: 123456\n", encoding="utf-8")
            import subprocess
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            self.assertFalse(GUARD.audit(root)["safe"])

    def test_audit_accepts_safe_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.md").write_text("documentação técnica sem dados reais\n", encoding="utf-8")
            import subprocess
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            self.assertTrue(GUARD.audit(root)["safe"])


if __name__ == "__main__":
    unittest.main()
