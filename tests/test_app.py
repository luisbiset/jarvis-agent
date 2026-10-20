import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from aghuse_assistant.app import main
from aghuse_assistant.gateway import ToolGateway, register_local_analysis_tools


class AppTests(unittest.TestCase):
    def run_cli(self, workspace: Path, *arguments: str) -> dict:
        output = io.StringIO()
        with patch.object(sys, "argv", ["aghuse-assistant", *arguments]), patch("pathlib.Path.cwd", return_value=workspace), redirect_stdout(output):
            self.assertEqual(main(), 0)
        return json.loads(output.getvalue())

    def test_analyze_plan_keeps_complete_artifact_in_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "feature.txt").write_text("cálculo de alta", encoding="utf-8")
            result = self.run_cli(workspace, "/analisar cálculo de alta", "--plan")
        self.assertEqual(result["operation"], "ANALYZE_AND_PLAN")
        self.assertEqual(result["state"], "SUCCEEDED")
        self.assertEqual(result["data"]["analysis"]["data"]["investigation_status"], "COMPLETE")
        self.assertEqual(result["data"]["planning"]["operation"], "PLAN")

    def test_analyze_plan_does_not_plan_incomplete_analysis(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(Path(temp_dir), "/analisar requisito ausente", "--plan")
        self.assertEqual(result["state"], "WAITING_INPUT")
        self.assertEqual(result["data"]["analysis"]["data"]["investigation_status"], "PARTIAL")
        self.assertEqual(result["data"]["planning"]["summary"], "Análise deve estar COMPLETE antes de planejar")

    def test_existing_plan_command_still_requires_an_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_cli(Path(temp_dir), "/planejar objetivo")
        self.assertEqual(result["operation"], "PLAN")
        self.assertEqual(result["state"], "WAITING_INPUT")

    def test_local_search_is_read_only_and_returns_workspace_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            source = workspace / "source.txt"
            source.write_text("linha com termo", encoding="utf-8")
            gateway = ToolGateway()
            register_local_analysis_tools(gateway, workspace)
            result = gateway.invoke("code.search", query={"requirement_id": "REQ-01", "term": "área: termo"})
            self.assertEqual(source.read_text(encoding="utf-8"), "linha com termo")
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.data[0]["source"], {"path": "source.txt", "line": 1})
        self.assertTrue(gateway.select(capability="analysis", read_only=True))


if __name__ == "__main__":
    unittest.main()
