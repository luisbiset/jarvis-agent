from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardContractTest(unittest.TestCase):
    def test_dashboard_exposes_shared_metrics_contract(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_test", ROOT / "scripts/jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            result = module.dashboard(Path(temporary) / "missing.db")
        self.assertEqual(result["metrics_contract"]["schema_version"], "1.0.0")
        self.assertEqual(result["metrics_contract"]["unknown_value"], "UNKNOWN/NOT_OBSERVED")


if __name__ == "__main__":
    unittest.main()
