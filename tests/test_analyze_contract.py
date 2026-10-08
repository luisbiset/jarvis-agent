import sys
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from aghuse_assistant.operations.analyze_contract import DemandContext, InvestigationLimits, evidence, impact, interpret_demand, investigate_progressively, metrics, validate_coverage
from aghuse_assistant.operations.analyze import execute
from aghuse_assistant.runtime.run import OperationRun

class AnalyzeContractTests(unittest.TestCase):
    def test_anonymized_drg_fixture_preserves_unknown_boundary(self):
        fixture = Path(__file__).parent / "fixtures" / "analyze" / "drg-56213.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertEqual(payload["task_ref"], "56213")
        context = interpret_demand("\n".join(item["question"] for item in payload["requirements"]))
        result = validate_coverage(context.requirements, [evidence("REQ-01", "QueryBuilder", "builder localizado")], [], limitations=[])
        self.assertEqual(result["status"], "PARTIAL")
    def test_interprets_explicit_requirements_without_inventing(self):
        context = interpret_demand("Bug: stack trace no serviço; confirmar causa raiz")
        self.assertEqual(context.demand_type, "bug")
        self.assertEqual([r.id for r in context.requirements], ["REQ-01", "REQ-02"])
        self.assertEqual(context.investigation_objective, "causa raiz")

    def test_coverage_detects_ignored_requirements_and_unsupported_facts(self):
        context = interpret_demand("verificar entidade\nverificar relatório")
        finding = evidence("REQ-01", "Entity", "campo observado", path="Entity.java", line=10)
        result = validate_coverage(context.requirements, [finding], [impact("Entity", "model", "REQUIRED", "regra confirmada", requirement_id="REQ-01")])
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["requirements_pending"], ["REQ-02"])

    def test_access_failure_is_blocked_and_unknown_is_explicit(self):
        context = interpret_demand("analisar impacto")
        result = validate_coverage(context.requirements, [], [], limitations=["Redmine inacessível"], access_blocked=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("UNKNOWN", metrics()["model"])

    def test_impact_states_are_closed(self):
        self.assertEqual(impact("DAO", "persistência", "NO_CHANGE", "somente consumidor")["classification"], "NO_CHANGE")
        with self.assertRaises(ValueError): impact("DAO", "persistência", "ALTERAR", "não")

    def test_progressive_investigation_records_empty_results_and_adapter_failures(self):
        def adapter(query):
            if query["area"] == "redmine":
                raise ConnectionError("offline")
            return []
        trace = investigate_progressively(
            [{"area": "redmine", "term": "56213"}, {"area": "code", "term": "Observacao"}],
            adapter,
            limits=InvestigationLimits(max_steps=2, max_mcp_calls=2),
        )
        self.assertEqual(trace.calls, 2)
        self.assertEqual(len(trace.no_occurrences), 1)
        self.assertTrue(trace.limitations)

    def test_progressive_investigation_exposes_budget_limit(self):
        trace = investigate_progressively(
            [{"area": "code", "term": "a"}, {"area": "code", "term": "b"}],
            lambda _query: [],
            limits=InvestigationLimits(max_steps=1, max_mcp_calls=1),
        )
        self.assertIn("limit", trace.limitations[0].casefold())

    def test_progressive_investigation_expands_follow_up_queries(self):
        seen = []
        def adapter(query):
            seen.append(query["term"])
            if query["term"] == "root":
                return [{"requirement_id": "REQ-01", "component": "QueryBuilder", "conclusion": "builder found", "type": "CODE", "source_id": "Q.java:10", "source": {"path": "Q.java", "line": 10}, "follow_up_queries": [{"area": "dto", "term": "DTO", "requirement_id": "REQ-01"}]}]
            return [{"requirement_id": "REQ-01", "component": "DTO", "conclusion": "mapping found", "type": "CODE", "source_id": "D.java:20", "source": {"path": "D.java", "line": 20}}]
        trace = investigate_progressively([{"area": "code", "term": "root", "requirement_id": "REQ-01"}], adapter)
        self.assertEqual(seen, ["root", "DTO"])
        self.assertEqual(trace.calls, 2)

    def test_analyze_operation_consumes_adapter_and_keeps_read_only_contract(self):
        run = OperationRun("aghuse", "ANALYZE", "melhoria\nverificar campo")
        run.analysis_adapter = lambda query: [evidence(query["requirement_id"], "Entity", "campo observado", path="Entity.java", line=12)]
        result = execute(run)
        self.assertFalse(result.data["mutates"])
        self.assertEqual(result.data["coverage"]["status"], "COMPLETE")
        self.assertEqual(result.data["metrics"]["mcp_calls"], 2)

if __name__ == "__main__":
    unittest.main()
