from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_doctor():
    spec = importlib.util.spec_from_file_location("jarvis_doctor", ROOT / "scripts" / "doctor.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class DoctorTest(unittest.TestCase):
    def test_plugin_enabled_is_valid_without_explicit_mcp_section(self):
        doctor = load_doctor()
        self.assertEqual(doctor.redmine_diagnostic({}, True, "C:/jarvis/server.mjs"), (True, "plugin Redmine instalado e habilitado"))

    def test_explicit_mcp_path_has_priority(self):
        doctor = load_doctor()
        config = {"mcp_servers": {"redmine": {"args": ["C:/jarvis/server.mjs"]}}}
        self.assertEqual(doctor.redmine_diagnostic(config, True, "C:/jarvis/server.mjs"), (True, "MCP Redmine configurado via mcp_servers"))

    def test_wrong_path_without_plugin_fails(self):
        doctor = load_doctor()
        config = {"mcp_servers": {"redmine": {"args": ["C:/other/server.mjs"]}}}
        self.assertEqual(doctor.redmine_diagnostic(config, False, "C:/jarvis/server.mjs")[0], False)

    def test_missing_plugin_and_mcp_fails(self):
        doctor = load_doctor()
        self.assertEqual(doctor.redmine_diagnostic({}, False, "C:/jarvis/server.mjs")[0], False)

    def test_doctor_source_is_utf8_and_has_no_mojibake(self):
        text = (ROOT / "scripts" / "doctor.py").read_text(encoding="utf-8")
        self.assertNotRegex(text, "|".join(chr(value) for value in (0xC3, 0xC2, 0xFFFD)))
        self.assertIn(r"ATEN\u00c7\u00c3O", text)
        self.assertIn(r"Diagn\u00f3stico", text)

    def test_strict_exit_is_zero_in_current_installation(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "doctor.py"), "--strict"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotRegex(result.stdout, "|".join(chr(value) for value in (0xC3, 0xC2, 0xFFFD)))


if __name__ == "__main__":
    unittest.main()
