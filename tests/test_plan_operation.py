import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from aghuse_assistant.operations.plan import execute, preview
from aghuse_assistant.runtime.run import OperationRun


class PlanOperationTests(unittest.TestCase):
    def test_plan_runs_independently(self):
        run = OperationRun("aghuse", "PLAN", "definir abordagem")
        result = execute(run)
        self.assertEqual(result.operation_id, "PLAN")
        self.assertFalse(result.metadata["mutates"])

    def test_plan_preview_has_no_workflow_dependency(self):
        result = preview("aghuse", {"objective": "definir abordagem"})
        self.assertEqual(result["operation"], "PLAN")
        self.assertFalse(result["mutates"])


if __name__ == "__main__":
    unittest.main()
