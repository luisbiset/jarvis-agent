import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from aghuse_assistant.analysis import AnalysisEngine
from aghuse_assistant.analysis.evidence import is_confirmed, normalize
from aghuse_assistant.analysis.interpreter import interpret
from aghuse_assistant.analysis.planner import plan
from aghuse_assistant.analysis.strategies import AghuseStrategy, GenericStrategy
from aghuse_assistant.gateway import ToolGateway, ToolSpec
from aghuse_assistant.orchestrator import ExecutionContext


def finding(requirement_id="REQ-01"):
    return {
        "requirement_id": requirement_id,
        "component": "ContaON",
        "classification": "REQUIRED",
        "conclusion": "regra localizada",
        "type": "CODE",
        "source_id": "src/ContaON.java:10",
        "source": {"path": "src/ContaON.java", "line": 10},
    }


class InterpreterTests(unittest.TestCase):
    def test_interprets_supported_demand_types_and_ambiguity(self):
        for text, expected in (("erro no cálculo", "bug"), ("melhoria na tela", "melhoria"), ("migração do fluxo", "migração"), ("refatorar serviço", "refatoração")):
            self.assertEqual(interpret(text).demand_type, expected)
        self.assertEqual(interpret("").ambiguities, ("Descrição técnica ausente",))


class PlannerTests(unittest.TestCase):
    def test_generic_plan_is_explicit_and_ordered(self):
        investigation = plan(interpret("investigar cálculo"), GenericStrategy())
        self.assertEqual([step.area for step in investigation.steps], ["código"])
        self.assertEqual(investigation.steps[0].depends_on, ())

    def test_aghuse_strategy_adds_domain_areas_without_changing_generic(self):
        demand = interpret("investigar cálculo")
        self.assertIn("ON/RN", [step.area for step in plan(demand, AghuseStrategy()).steps])
        self.assertNotIn("ON/RN", [step.area for step in plan(demand, GenericStrategy()).steps])


class EvidenceTests(unittest.TestCase):
    def test_requires_source_requirement_and_conclusion(self):
        self.assertTrue(is_confirmed(finding()))
        self.assertFalse(is_confirmed(normalize({"type": "CODE", "conclusion": "x"}, "REQ-01")))


class EngineTests(unittest.TestCase):
    def test_no_tools_is_blocked(self):
        result = AnalysisEngine().execute(ExecutionContext("other", "ANALYZE", "investigar"), ToolGateway())
        self.assertEqual(result.coverage.status, "BLOCKED")
        self.assertEqual(result.trace.areas_examined, [])

    def test_complete_requires_verified_evidence(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=lambda query: [finding(query["requirement_id"])]))
        result = AnalysisEngine().execute(ExecutionContext("other", "ANALYZE", "investigar"), gateway)
        self.assertEqual(result.coverage.status, "COMPLETE")
        self.assertEqual(result.affected_files, ("src/ContaON.java",))

    def test_partial_failure_preserves_other_evidence(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=lambda query: [finding(query["requirement_id"])]))
        gateway.register(ToolSpec("git.search", "analysis", "workspace", handler=lambda **_: (_ for _ in ()).throw(RuntimeError("indisponível"))))
        result = AnalysisEngine().execute(ExecutionContext("other", "ANALYZE", "investigar"), gateway)
        self.assertEqual(result.coverage.status, "PARTIAL")
        self.assertEqual(len(result.evidence), 1)

    def test_write_tools_are_never_selected(self):
        gateway = ToolGateway()
        gateway.register(ToolSpec("code.write", "analysis", "workspace", read_only=False, handler=lambda **_: self.fail("ferramenta de escrita executada")))
        result = AnalysisEngine().execute(ExecutionContext("other", "ANALYZE", "investigar"), gateway)
        self.assertEqual(result.coverage.status, "BLOCKED")

    def test_follow_ups_are_deduplicated_and_bounded(self):
        gateway = ToolGateway()
        def handler(query):
            item = finding(query["requirement_id"])
            item["follow_up_queries"] = [{"area": "código", "term": "mesma consulta"}, {"area": "código", "term": "mesma consulta"}]
            return [item]
        gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=handler))
        context = ExecutionContext("other", "ANALYZE", "investigar", parameters={"analysis_limits": {"max_steps": 2}})
        result = AnalysisEngine().execute(context, gateway)
        self.assertLessEqual(len(result.trace.executed_steps), 2)


if __name__ == "__main__":
    unittest.main()
