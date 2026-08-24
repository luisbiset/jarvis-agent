from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "run_evals.py"
SPEC = importlib.util.spec_from_file_location("run_evals", MODULE_PATH)
assert SPEC and SPEC.loader
EVALS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVALS)


class RoutingEvalTest(unittest.TestCase):
    def case(self):
        return {
            "expected_skills": ["aghuse-development"],
            "expected_agents": ["aghuse_frontend"],
            "allowed_agents": [],
            "forbidden_agents": ["aghuse_database"],
            "expected_stages": [{"mode": "sequential", "agents": ["aghuse_frontend"]}],
            "complexity": "TRIVIAL",
            "risk_class": "LOW",
            "operational_mode": "ASSISTED_AUTOPILOT",
            "reasoning_class": "NORMAL",
            "max_agents": 1,
            "max_parallel_agents": 1,
            "stop_reason": None,
            "requires_confirmation": False,
            "read_only": False,
            "invariants": [],
        }

    def actual(self):
        return {
            "skills": ["aghuse-agent:aghuse-development"],
            "agents": ["aghuse_frontend"],
            "stages": [{"mode": "sequential", "agents": ["aghuse_frontend"]}],
            "complexity": "TRIVIAL",
            "risk_class": "LOW",
            "operational_mode": "ASSISTED_AUTOPILOT",
            "reasoning_class": "NORMAL",
            "max_agents": 1,
            "max_parallel_agents": 1,
            "stop_reason": None,
            "requires_confirmation": False,
            "read_only": False,
            "invariants": [],
        }

    def test_accepts_exact_v2_routing(self):
        errors, scores = EVALS.compare(self.case(), self.actual())
        self.assertEqual(errors, [])
        self.assertTrue(all(scores.values()))

    def test_detects_over_routing_even_when_required_agent_exists(self):
        actual = self.actual()
        actual["agents"].append("aghuse_database")
        errors, scores = EVALS.compare(self.case(), actual)
        self.assertTrue(any("over-routing" in error for error in errors))
        self.assertFalse(scores["over_routing"])

    def test_detects_stage_order(self):
        actual = self.actual()
        actual["stages"] = [{"mode": "parallel", "agents": ["aghuse_frontend"]}]
        _, scores = EVALS.compare(self.case(), actual)
        self.assertFalse(scores["stage_order"])


if __name__ == "__main__":
    unittest.main()
