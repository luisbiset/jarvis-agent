import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.orchestrator import ExecutionContext, ExecutionState, Orchestrator


class OrchestratorGatewayTests(unittest.TestCase):
    def test_read_only_flow_uses_analysis_team(self):
        result = Orchestrator().execute(Orchestrator().create({"operation": "ANALYZE", "objective": "investigar"}))
        self.assertEqual(result.state, ExecutionState.SUCCEEDED)
        self.assertFalse(result.data["mutates"])
        self.assertEqual(result.data["investigation_status"], "BLOCKED")

    def test_analysis_uses_only_registered_read_only_gateway_tools(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=lambda query: [{
            "requirement_id": query["requirement_id"],
            "component": "ContaON",
            "classification": "REQUIRED",
            "conclusion": "regra localizada",
            "type": "CODE",
            "source_id": "src/ContaON.java:10",
            "source": {"path": "src/ContaON.java", "line": 10},
            "matched_terms": ["calculo"],
        }]))
        gateway.register(ToolSpec("code.write", "analysis", "workspace", read_only=False, handler=lambda **_: self.fail("write tool invoked")))
        orchestrator = Orchestrator(gateway=gateway)
        result = orchestrator.execute(orchestrator.create({"operation": "ANALYZE", "objective": "investigar cálculo"}))
        self.assertEqual(result.data["investigation_status"], "COMPLETE")
        self.assertEqual(result.data["affected_files"], ["src/ContaON.java"])
        self.assertGreaterEqual(result.data["metrics"]["mcp_calls"], 1)

    def test_mutating_flow_requires_checkpoint(self):
        orchestrator = Orchestrator()
        context = orchestrator.create({"operation": "IMPLEMENT", "objective": "alterar"})
        self.assertEqual(orchestrator.execute(context).state, ExecutionState.WAITING_INPUT)
        self.assertEqual(orchestrator.execute(context, confirm=True).state, ExecutionState.WAITING_INPUT)

    def test_plan_requires_complete_analysis_artifact(self):
        result = Orchestrator().execute(Orchestrator().create({"operation": "PLAN", "objective": "planejar"}))
        self.assertEqual(result.state, ExecutionState.WAITING_INPUT)

    def test_gateway_requires_confirmation_for_writes(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("redmine.update", "redmine", "project", read_only=False, confirmation_required=True, handler=lambda: {"ok": True}))
        self.assertEqual(gateway.invoke("redmine.update").status, "WAITING_INPUT")
        self.assertEqual(gateway.invoke("redmine.update", confirm=True).status, "SUCCEEDED")

    def test_gateway_normalizes_failures(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("build.test", "build", "workspace", handler=lambda: (_ for _ in ()).throw(RuntimeError("failed"))))
        self.assertEqual(gateway.invoke("build.test").status, "FAILED")

    def test_contexts_do_not_share_artifacts_or_parameters(self):
        first = ExecutionContext("aghuse", "VALIDATE", "x")
        second = ExecutionContext("aghuse", "VALIDATE", "y")
        first.artifacts["implementation"] = {"id": "one"}
        first.parameters["files"] = ["a.py"]
        self.assertEqual(second.artifacts, {})
        self.assertEqual(second.parameters, {})


if __name__ == "__main__":
    unittest.main()
