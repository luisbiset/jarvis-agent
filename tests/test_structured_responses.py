import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from aghuse_assistant.api import RunService
from aghuse_assistant.runtime.responses import ResponseContractError, OPERATIONS, parse_response
from aghuse_assistant.runtime.provider import StructuredProvider
from aghuse_assistant.runtime.run import OperationRun


def payload(operation):
    values = {key: [] for key in OPERATIONS[operation]}
    if operation == "ANALYZE":
        values["impact"] = "baixo"
        values["coverage"] = {"analyzed": [], "pending": [], "no_occurrences": [], "not_investigated": [], "searched_terms": [], "limitations": []}
    if operation == "PLAN": values["objective"] = "objetivo"
    if operation == "VALIDATE": values["recommendation"] = "seguir"
    if operation == "IMPLEMENT":
        values["approval_required"] = False
        values["rollback_notes"] = ""
    if operation == "MANUTENCAO":
        values.update({"approval_required": True, "rollback_notes": "x", "scope": "assistant-only", "agent": "aghuse_assistant"})
    return json.dumps({"schema_version": "1.0.0", "operation": operation, "status": "SUCCEEDED", "summary": "ok", "data": values, "warnings": [], "evidence": []})


class Provider:
    def __init__(self, responses): self.responses, self.calls = list(responses), 0
    def execute(self, run, schema):
        self.calls += 1
        from aghuse_assistant.runtime.responses import parse_response
        raw = self.responses.pop(0)
        return parse_response(raw, run.operation, run.run_id, run.project, self.calls)


class StructuredResponseTests(unittest.TestCase):
    def test_each_operation_has_a_contract(self):
        for operation in OPERATIONS:
            result = parse_response(payload(operation), operation, "aghuse-run", "aghuse", 1)
            self.assertTrue(result["validation"]["schema_valid"])
            self.assertEqual(set(OPERATIONS[operation]), set(result["data"]))

    def test_mismatched_operation_and_forbidden_metadata_are_rejected(self):
        with self.assertRaises(ResponseContractError):
            parse_response(payload("PLAN"), "ANALYZE", "run", "aghuse", 1)
        forbidden = json.loads(payload("PLAN")); forbidden["data"]["steps"] = ["AGENTS.md"]
        with self.assertRaises(ResponseContractError):
            parse_response(forbidden, "PLAN", "run", "aghuse", 1)

    def test_runtime_persists_only_valid_structured_result(self):
        provider = Provider([payload("ANALYZE")])
        service = RunService(provider=provider)
        run = service.create({"project": "aghuse", "operation": "ANALYZE", "objective": "investigar"})
        result = service.execute(run["run_id"])
        self.assertEqual(result["result"]["operation"], "ANALYZE")
        self.assertTrue(result["result"]["validation"]["schema_valid"])

    def test_analyze_rejects_invalid_impact_classification(self):
        value = json.loads(payload("ANALYZE"))
        value["data"]["impact_matrix"] = [{"component":"X", "role":"DAO", "classification":"ALTERAR", "change":"UNKNOWN", "justification":"j", "evidence":[], "status":"UNKNOWN"}]
        with self.assertRaises(ResponseContractError):
            parse_response(value, "ANALYZE", "run", "aghuse", 1)

    def test_analyze_requires_impact_evidence_fields(self):
        value = json.loads(payload("ANALYZE"))
        value["data"]["impact_matrix"] = [{"component":"X", "role":"DAO", "classification":"NÃO CONFIRMADO", "change":"UNKNOWN", "justification":"j", "evidence":[], "status":"UNKNOWN"}]
        del value["data"]["impact_matrix"][0]["justification"]
        with self.assertRaises(ResponseContractError):
            parse_response(value, "ANALYZE", "run", "aghuse", 1)

    def test_invalid_response_retries_once_and_accepts_correction(self):
        responses = iter(["not-json", payload("PLAN")])
        provider = StructuredProvider(lambda _prompt: next(responses))
        result = provider.execute(OperationRun("aghuse", "PLAN", "planejar"), {"required": list(OPERATIONS["PLAN"])})
        self.assertEqual(result["validation"]["attempts"], 2)

    def test_two_invalid_responses_fail_without_result(self):
        provider = StructuredProvider(lambda _prompt: "not-json")
        with self.assertRaises(ResponseContractError):
            provider.execute(OperationRun("aghuse", "PLAN", "planejar"), {})


if __name__ == "__main__":
    unittest.main()
