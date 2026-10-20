import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.orchestrator import ExecutionContext, ExecutionState
from aghuse_assistant.validation import ValidationEngine
from aghuse_assistant.validation.result import to_execution


class ValidationTests(unittest.TestCase):
    def test_uses_only_read_only_tools(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("test.run", "validation", "workspace", handler=lambda **_: {"status": "PASSED"}))
        gateway.register(ToolSpec("code.fix", "validation", "workspace", read_only=False, handler=lambda **_: self.fail("write invoked")))
        result = ValidationEngine().execute(ExecutionContext("aghuse", "VALIDATE", "validar", parameters={"files": ["a.py"]}), gateway)
        self.assertEqual(len(result.passed), 1)

    def test_distinguishes_failure_warning_and_regression(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("test.run", "validation", "workspace", handler=lambda **_: {"status": "FAILED", "critical": True, "warnings": ["lento"], "regressions": [{"description": "quebra"}]}))
        result = ValidationEngine().execute(ExecutionContext("aghuse", "VALIDATE", "validar"), gateway)
        self.assertTrue(result.failed)
        self.assertTrue(result.warnings)
        self.assertTrue(result.regressions)
        self.assertEqual(result.recommendation, "Retornar ao desenvolvimento")
        execution = to_execution(ExecutionContext("aghuse", "VALIDATE", "validar"), result)
        self.assertEqual(execution.state, ExecutionState.FAILED)

    def test_blocks_when_no_validation_tool_is_registered(self):
        result = ValidationEngine().execute(ExecutionContext("aghuse", "VALIDATE", "validar"), ToolGateway())
        self.assertTrue(result.failed)
        self.assertTrue(result.failed[0]["critical"])
        self.assertEqual(result.recommendation, "Retornar ao desenvolvimento")
        self.assertEqual(to_execution(ExecutionContext("aghuse", "VALIDATE", "validar"), result).state, ExecutionState.FAILED)

    def test_rejects_invalid_validation_status(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("test.run", "validation", "workspace", handler=lambda **_: {"status": "UNKNOWN"}))
        result = ValidationEngine().execute(ExecutionContext("aghuse", "VALIDATE", "validar"), gateway)
        self.assertTrue(result.failed)
        self.assertTrue(result.failed[0]["critical"])
        self.assertEqual(to_execution(ExecutionContext("aghuse", "VALIDATE", "validar"), result).state, ExecutionState.FAILED)
