import unittest

from scripts.operations import catalog, create_preview, validate


class OperationsTests(unittest.TestCase):
    def test_catalog_contains_maintenance_operation(self):
        self.assertEqual({item["operation_id"] for item in catalog()}, {"ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE", "MANUTENCAO"})

    def test_maintenance_requires_only_objective_and_uses_checkpoint_policy(self):
        self.assertEqual(validate("MANUTENCAO", {"objective": "atualizar skill"})["objective"], "atualizar skill")
        proposal = create_preview("MANUTENCAO", "aghuse", {"objective": "atualizar skill"}, rag={}, metrics={}, provider="cli")
        self.assertTrue(proposal["requires_checkpoint"])
        self.assertEqual(proposal["allowed_agents"], ["aghuse_assistant"])

    def test_implement_requires_acceptance_criteria(self):
        with self.assertRaisesRegex(ValueError, "acceptance_criteria"):
            validate("IMPLEMENT", {"objective": "corrigir regra"})

    def test_preview_keeps_only_safe_metadata(self):
        proposal = create_preview("PLAN", "aghuse", {"objective": "analisar arquitetura", "secret": "não persistir"}, rag={"retrieved": True, "query_id": "q-1", "hits": [{"path": "safe.py"}]}, metrics={"initial": {"model": "gpt-5.6-terra", "reasoning": "medium"}}, provider="cli")
        self.assertEqual(proposal["status"], "PROPOSAL_READY")
        self.assertNotIn("secret", proposal)
        self.assertNotIn("prompt", proposal)
        self.assertEqual(proposal["model_requested"], "gpt-5.6-terra")


if __name__ == "__main__":
    unittest.main()
