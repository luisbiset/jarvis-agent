import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

class SkillContractTests(unittest.TestCase):
    def test_operational_skills_require_structured_json(self):
        expected = {"analisar": "ANALYZE", "planejar": "PLAN", "implementar": "IMPLEMENT", "validar": "VALIDATE"}
        for skill, operation in expected.items():
            skill_text = (ROOT / "plugins/aghuse-assistant/skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            ui_text = (ROOT / "plugins/aghuse-assistant/skills" / skill / "agents/openai.yaml").read_text(encoding="utf-8")
            self.assertIn("Contrato de resposta", skill_text)
            self.assertIn("Gere internamente um objeto JSON", skill_text)
            self.assertIn(operation, skill_text)
            self.assertIn(f"${skill}", ui_text)
            self.assertIn(operation, ui_text)
            self.assertIn("Markdown", skill_text)

    def test_analyze_task_number_is_context_not_redmine_operation(self):
        skill_text = (ROOT / "plugins/aghuse-assistant/skills/analisar/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("task_ref", skill_text)
        self.assertIn("contrato ANALYZE completo", skill_text)
        self.assertIn("O objeto final da operacao", skill_text)
        self.assertIn("nao use `list_issues` ou `get_issue` como operacao final", skill_text)
        self.assertIn("matriz", skill_text.lower())

if __name__ == "__main__": unittest.main()
