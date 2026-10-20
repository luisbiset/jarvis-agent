import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.implementation import ImplementationEngine, ImplementationInputError
from aghuse_assistant.orchestrator import ExecutionAuthorization, ExecutionContext, ExecutionState
from aghuse_assistant.implementation.result import to_execution


def approved_plan(*steps):
    return {"objective": "alterar", "assumptions": [], "steps": list(steps), "dependencies": [], "acceptance_criteria": [], "validation_plan": [], "risks": [], "approved": True}


class ImplementationTests(unittest.TestCase):
    def test_mutation_requires_authorization(self):
        with self.assertRaises(ImplementationInputError):
            ImplementationEngine().execute(ExecutionContext("aghuse", "IMPLEMENT", "alterar"), ToolGateway(), ExecutionAuthorization())

    def test_executes_mutating_tool_after_confirmation(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("code.edit", "implementation", "workspace", read_only=False, confirmation_required=True, handler=lambda **_: {"changes": [{"description": "feito"}], "files_changed": ["a.py"]}, rollback_handler=lambda **_: None))
        result = ImplementationEngine().execute(ExecutionContext("aghuse", "IMPLEMENT", "alterar", artifacts={"plan": approved_plan({"id": "STEP-01", "description": "alterar", "classification": "REQUIRED"})}), gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertEqual(result.files_changed, ("a.py",))

    def test_failure_executes_rollback_and_returns_failed_state(self):
        gateway = ToolGateway()
        rolled_back = []
        gateway.register(ToolSpec("a.edit", "implementation", "workspace", read_only=False, handler=lambda **_: {"changes": [{"description": "feito"}], "files_changed": ["a.py"]}, rollback_handler=lambda **_: rolled_back.append("a.edit")))
        gateway.register(ToolSpec("b.edit", "implementation", "workspace", read_only=False, handler=lambda **_: (_ for _ in ()).throw(RuntimeError("falha")), rollback_handler=lambda **_: None))
        context = ExecutionContext("aghuse", "IMPLEMENT", "alterar", artifacts={"plan": approved_plan({"id": "STEP-01", "description": "alterar A", "classification": "REQUIRED", "tool": "a.edit"}, {"id": "STEP-02", "description": "alterar B", "classification": "REQUIRED", "tool": "b.edit"})})
        result = ImplementationEngine().execute(context, gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertEqual(result.files_changed, ())
        self.assertTrue(result.pending_items)
        self.assertEqual(rolled_back, ["a.edit"])
        self.assertEqual(to_execution(context, result).state, ExecutionState.FAILED)

    def test_rejects_direct_implementation_and_external_tool(self):
        with self.assertRaises(ImplementationInputError):
            ImplementationEngine().execute(ExecutionContext("aghuse", "IMPLEMENT", "alterar"), ToolGateway(), ExecutionAuthorization(mutation_confirmed=True))
        gateway = ToolGateway()
        gateway.register(ToolSpec("external.edit", "implementation", "external", read_only=False, handler=lambda **_: self.fail("ferramenta externa invocada"), rollback_handler=lambda **_: None))
        context = ExecutionContext("aghuse", "IMPLEMENT", "alterar", artifacts={"plan": approved_plan({"id": "STEP-01", "description": "alterar", "classification": "REQUIRED"})})
        result = ImplementationEngine().execute(context, gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertTrue(result.pending_items)
        self.assertEqual(to_execution(context, result).state, ExecutionState.FAILED)
