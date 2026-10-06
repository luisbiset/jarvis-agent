import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from runtime.execution_planner import compare_strategies, plan_execution


class ExecutionPlannerTests(unittest.TestCase):
    def test_trivial_uses_one_specialist_without_review(self):
        plan = plan_execution({"complexity": "TRIVIAL", "task_type": "TEST", "risk_class": "LOW"})
        self.assertEqual(plan["agents_planned"], ["aghuse_testes"])
        self.assertFalse(plan["review_required"])
        self.assertEqual(plan["retry_policy"], "NONE")

    def test_localized_contract_requires_review(self):
        plan = plan_execution({"complexity": "LOCALIZED", "task_type": "BACKEND", "contract_changed": True})
        self.assertEqual(len(plan["agents_planned"]), 1)
        self.assertTrue(plan["review_required"])

    def test_transversal_has_distinct_reviewer(self):
        plan = plan_execution({"complexity": "TRANSVERSAL", "task_type": "BACKEND"})
        self.assertIn("aghuse_qualidade", plan["agents_planned"])
        self.assertNotEqual(plan["agents_planned"][1], "aghuse_qualidade")

    def test_shadow_does_not_execute_alternative(self):
        current = plan_execution({"complexity": "CRITICAL", "task_type": "DATABASE"})
        optimized = plan_execution({"complexity": "LOCALIZED", "task_type": "DATABASE"})
        result = compare_strategies(current, optimized)
        self.assertFalse(result["alternative_executed"])
        self.assertIn("quality_delta", result)


if __name__ == "__main__":
    unittest.main()
