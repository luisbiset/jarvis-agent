import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from aghuse_assistant.runtime.renderers import render

class RendererTests(unittest.TestCase):
    def envelope(self, operation, data):
        return {"schema_version":"1.0.0", "operation":operation, "run_id":"secret-run", "summary":"Resumo seguro", "data":data, "validation":{"schema_valid":True,"attempts":1}}

    def test_analyze_renders_status_impact_matrix_and_coverage(self):
        text = render(self.envelope("ANALYZE", {"impact":"causa provável", "affected_files":["ContaHospitalarON.java"], "database":None, "risks":[{"severity":"MEDIUM","description":"risco"}], "recommendations":["Revisar X"], "findings":[{"summary":"achado"}], "evidence":[{"path":"ContaHospitalarON.java","line":10,"description":"campo observado"}], "impact_matrix":[{"component":"McoNascimentos.java","role":"Mapeamento JPA","classification":"REQUIRED","change":"Aumentar limite","justification":"Limite explícito","evidence":[{"path":"McoNascimentos.java","symbol":"observacao","line":10,"description":"length=1000"}],"status":"CONFIRMED"}], "coverage":{"status":"COMPLETE","analyzed":["entidades"],"pending":[],"no_occurrences":[],"not_investigated":[],"searched_terms":["observacao"],"limitations":[]}}))
        self.assertIn("# ANÁLISE TÉCNICA", text)
        self.assertIn("### Matriz de impacto", text)
        self.assertIn("REQUIRED", text)
        self.assertIn("### Cobertura da investigação", text)
        self.assertIn("COMPLETE", text)
        self.assertNotIn("secret-run", text)

    def test_all_operation_renderers_return_markdown_text(self):
        fields = {"PLAN":{"objective":"x","assumptions":[],"steps":[],"dependencies":[],"acceptance_criteria":[],"validation_plan":[],"risks":[]}, "IMPLEMENT":{"changes":[],"files_changed":[],"tests_executed":[],"tests_passed":[],"pending_items":[],"rollback_notes":"x","approval_required":False}, "VALIDATE":{"checks":[],"passed":[],"failed":[],"warnings":[],"regressions":[],"evidence":[],"recommendation":"x"}}
        for operation, data in fields.items():
            output = render(self.envelope(operation, data))
            self.assertIsInstance(output, str)
            self.assertNotIn('"operation"', output)

if __name__ == "__main__": unittest.main()
