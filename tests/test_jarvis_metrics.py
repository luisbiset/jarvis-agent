from __future__ import annotations

import unittest

from scripts.jarvis_metrics import UNKNOWN, final, human, initial, policy_decision, rag_metrics


class MetricsTest(unittest.TestCase):
    def test_initial_line_never_turns_unknown_credits_into_zero(self):
        metrics = initial("corrigir DAO", rag={"required": True}, decision={"complexity": "LOCALIZED", "risk_class": "LOW", "operational_mode": "COPILOT", "model": "model-x", "reasoning_effort": "medium", "max_agents": 2})
        self.assertEqual(metrics["credits"], UNKNOWN)
        self.assertIn("créditos UNKNOWN/NOT_OBSERVED", human(metrics))

    def test_policy_decision_supplies_model_and_reasoning_without_usage(self):
        decision = policy_decision(technical=True)
        self.assertEqual(decision["model"], "gpt-5.6-terra")
        self.assertEqual(decision["reasoning_effort"], "medium")
        self.assertEqual(decision["max_attempts"], 3)

    def test_final_without_execution_is_explicit(self):
        metrics = final(initial("teste", rag={}), reason="NOT_EXECUTED")
        self.assertEqual(metrics["phase"], "FINAL")
        self.assertEqual(metrics["data_quality"], "NOT_EXECUTED")
        self.assertEqual(metrics["duration_ms"], UNKNOWN)

    def test_rag_states_are_safe_and_do_not_expose_hits(self):
        blocked = rag_metrics({"required": True, "reason": "rag_index_not_found"})
        bypass = rag_metrics({"required": True, "bypassed": True, "bypass_reason": "maintenance"})
        used = rag_metrics({"required": True, "retrieved": True, "retrieval_mode": "LEXICAL_ONLY", "hits": [{"text": "secret"}]})
        self.assertEqual(blocked["data_quality"], "RAG_BLOCKED")
        self.assertEqual(bypass["data_quality"], "RAG_BYPASS_AUTHORIZED")
        self.assertEqual(used["selected_chunks"], 1)
        self.assertNotIn("secret", str(used))

    def test_final_preserves_reasoning_transition_and_observed_usage(self):
        start = initial("impl", rag={}, decision={"reasoning_effort": "medium", "max_agents": 2, "max_attempts": 3})
        end = final(start, reason="COMPLETED", state={"metrics": {"retry_count": 1, "agent_invocation_count": 2, "duration_ms": 120, "credits": 1.5}, "budget": {"max_model_calls": 3, "max_agents": 2}, "reasoning": {"effective_reasoning": "high"}})
        self.assertEqual(end["attempts_used"], 2)
        self.assertEqual(end["credits_status"], "OBSERVED")
        self.assertEqual(end["reasoning"], "medium->high")


if __name__ == "__main__":
    unittest.main()
