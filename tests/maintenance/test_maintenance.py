import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.maintenance import MaintenanceEngine, MaintenanceInputError
from aghuse_assistant.orchestrator import ExecutionAuthorization, ExecutionContext


class MaintenanceTests(unittest.TestCase):
    def test_rejects_other_projects(self):
        with self.assertRaises(MaintenanceInputError):
            MaintenanceEngine().execute(ExecutionContext("aghuse", "MANUTENCAO", "alterar"), ToolGateway(), ExecutionAuthorization(mutation_confirmed=True))

    def test_blocks_external_tool_scope(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("redmine.update", "maintenance", "external", read_only=False, handler=lambda **_: self.fail("external tool invoked")))
        result = MaintenanceEngine().execute(ExecutionContext("aghuse-assistant", "MANUTENCAO", "alterar"), gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertIn("escopo externo bloqueado", result.pending_items[0])

    def test_executes_confirmed_assistant_only_tool(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("assistant.edit", "maintenance", "assistant-only", read_only=False, handler=lambda **_: {"changes": [{"description": "feito"}], "files_changed": ["README.md"]}))
        result = MaintenanceEngine().execute(ExecutionContext("aghuse-assistant", "MANUTENCAO", "alterar"), gateway, ExecutionAuthorization(mutation_confirmed=True))
        self.assertEqual(result.scope, "assistant-only")
        self.assertEqual(result.files_changed, ("README.md",))
