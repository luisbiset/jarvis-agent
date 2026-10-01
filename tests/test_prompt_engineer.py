import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("prompt_engineer", ROOT / "scripts/prompt_engineer.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PromptEngineerTest(unittest.TestCase):
    def test_structures_prompt_without_replacing_intent(self):
        result = module.improve_prompt("corrija o formulário de alta")
        self.assertTrue(result["changed"])
        self.assertIn("corrija o formulário de alta", result["enhanced"])
        self.assertIn("Não execute ações externas", result["enhanced"])

    def test_empty_prompt_is_safe(self):
        self.assertFalse(module.improve_prompt(" ")["changed"])


if __name__ == "__main__":
    unittest.main()
