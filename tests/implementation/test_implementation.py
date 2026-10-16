import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.implementation import ImplementationEngine, ImplementationInputError
from aghuse_assistant.orchestrator import ExecutionAuthorization, ExecutionContext


class ImplementationTests(unittest.TestCase):
    def test_mutation_requires_authorization(self):
        with self.assertRaises(ImplementationInputError):
            ImplementationEngine().execute(ExecutionContext("aghuse", "IMPLEMENT", "alterar"), ToolGateway(), ExecutionAuthorization())

    def test_executes_mutating_tool_after_confirmation(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("code.edit", "implementation", "workspace", read_only=False, confirmation_required=True, handler=lambda **_: {"changes": [{"description": "feito"}], "files_changed": ["a.py"]}))
        result = ImplementationEngine().execute(ExecutionContext("aghuse", "IMPLEMENT", "alterar"), gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertEqual(result.files_changed, ("a.py",))

    def test_partial_failure_preserves_changes_and_rollback(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("a.edit", "implementation", "workspace", read_only=False, handler=lambda **_: {"changes": [{"description": "feito"}], "files_changed": ["a.py"]}))
        gateway.register(ToolSpec("b.edit", "implementation", "workspace", read_only=False, handler=lambda **_: (_ for _ in ()).throw(RuntimeError("falha"))))
        result = ImplementationEngine().execute(ExecutionContext("aghuse", "IMPLEMENT", "alterar"), gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertEqual(result.files_changed, ("a.py",))
        self.assertTrue(result.pending_items)
        self.assertIn("a.py", result.rollback_notes)
