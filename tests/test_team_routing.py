from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "jarvis_runtime.py"
SPEC = importlib.util.spec_from_file_location("jarvis_runtime_team_test", MODULE_PATH)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class TeamRoutingTest(unittest.TestCase):
    def test_state_infers_official_team(self):
        self.assertEqual(RUNTIME.team_for_stage("DISCOVERY"), "ANALISE")
        self.assertEqual(RUNTIME.team_for_stage("IMPLEMENTING"), "DESENVOLVIMENTO")
        self.assertEqual(RUNTIME.team_for_stage("VALIDATING"), "REVISAO_QUALIDADE")
        self.assertIsNone(RUNTIME.team_for_stage("HUMAN_GATE"))

    def test_agent_outside_team_is_rejected(self):
        with self.assertRaises(RUNTIME.RuntimeErrorSafe):
            RUNTIME.resolve_team("VALIDATING", "aghuse_backend", None)

    def test_fast_path_selects_only_development(self):
        result = RUNTIME.team_route(argparse.Namespace(pattern="aghuse-jsf-label", include_optional=False))
        self.assertEqual([item["team"] for item in result["teams"]], ["DESENVOLVIMENTO"])
        self.assertEqual(result["agents"], ["aghuse_frontend"])
        self.assertEqual(result["coordination_model_calls"], 0)

    def test_optional_analysis_is_not_selected_by_default(self):
        result = RUNTIME.team_route(argparse.Namespace(pattern="aghuse-dao-criteria", include_optional=False))
        self.assertEqual([item["team"] for item in result["teams"]], ["DESENVOLVIMENTO", "REVISAO_QUALIDADE"])
        self.assertEqual(result["agents"], ["aghuse_database", "aghuse_qa"])


if __name__ == "__main__":
    unittest.main()
