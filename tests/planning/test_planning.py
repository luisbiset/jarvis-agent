import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from aghuse_assistant.analysis import AnalysisEngine
from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.orchestrator import ExecutionAuthorization, ExecutionContext, ExecutionState
from aghuse_assistant.operations.plan import execute
from aghuse_assistant.planning.models import PlanResult


def complete_analysis():
    gateway = ToolGateway()
    gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=lambda query: [{"requirement_id": query["requirement_id"], "component": "X", "classification": "REQUIRED", "conclusion": "ok", "type": "CODE", "source_id": "x.py:1", "source": {"path": "x.py", "line": 1}}]))
    return AnalysisEngine().execute(ExecutionContext("other", "ANALYZE", "objetivo"), gateway)


class PlanningTests(unittest.TestCase):
    def test_blocks_without_complete_analysis(self):
        result = execute(ExecutionContext("other", "PLAN", "planejar"), ToolGateway(), ExecutionAuthorization())
        self.assertEqual(result.state, ExecutionState.WAITING_INPUT)

    def test_accepts_serialized_complete_analysis(self):
        context = ExecutionContext("other", "PLAN", "planejar", artifacts={"analysis": complete_analysis().to_dict()})
        result = execute(context, ToolGateway(), ExecutionAuthorization())
        self.assertEqual(result.state, ExecutionState.SUCCEEDED)
        self.assertIn("acceptance_criteria", result.data)
        self.assertEqual(PlanResult.from_dict({**result.data, "approved": True}).approved, True)

    def test_invalid_artifact_is_rejected_before_tools(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("planning.read", "planning", "workspace", handler=lambda **_: self.fail("tool invoked")))
        result = execute(ExecutionContext("other", "PLAN", "x", artifacts={"analysis": {"bad": True}}), gateway, ExecutionAuthorization())
        self.assertEqual(result.state, ExecutionState.WAITING_INPUT)
