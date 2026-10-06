from __future__ import annotations

import importlib.util
import tempfile
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardContractTest(unittest.TestCase):
    def test_dashboard_exposes_shared_metrics_contract(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_test", ROOT / "scripts/jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            result = module.dashboard(Path(temporary) / "missing.db")
        self.assertEqual(result["metrics_contract"]["schema_version"], "1.0.0")
        self.assertEqual(result["metrics_contract"]["unknown_value"], "UNKNOWN/NOT_OBSERVED")

    def test_tasks_filters_and_detail_are_correlated(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_tasks", ROOT / "scripts/jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            db = Path(temporary) / "telemetry.db"
            connection = sqlite3.connect(db)
            try:
                connection.executescript("""
                    CREATE TABLE runs(run_id TEXT, task_id TEXT, status TEXT, complexity TEXT, risk_class TEXT, started_at TEXT, duration_ms INTEGER, credits REAL);
                    CREATE TABLE agent_invocations(run_id TEXT, agent TEXT, started_at TEXT);
                    CREATE TABLE transitions(run_id TEXT, target TEXT, at TEXT, reason TEXT);
                    CREATE TABLE findings(run_id TEXT, category TEXT);
                    CREATE TABLE execution_attempts(model_effective TEXT, effective_reasoning TEXT, input_tokens INTEGER, output_tokens INTEGER, credits REAL);
                """)
                connection.execute("INSERT INTO runs VALUES('r1','task-1','BLOCKED','CRITICAL','HIGH','2026-01-01',12,1.5)")
                connection.execute("INSERT INTO agent_invocations VALUES('r1','aghuse_backend','2026-01-01')")
                connection.execute("INSERT INTO transitions VALUES('r1','BLOCKED','2026-01-01','budget')")
                connection.execute("INSERT INTO findings VALUES('r1','TEST')")
                connection.execute("INSERT INTO execution_attempts VALUES('model-x','MEDIUM',100,30,0.5)")
                connection.commit()
            finally:
                connection.close()
            events = Path(temporary) / "runs" / "r1" / "events.jsonl"
            events.parent.mkdir(parents=True)
            events.write_text('{"event":"AGENT_INVOCATION_STARTED","agent":"aghuse_backend"}\n', encoding="utf-8")
            self.assertEqual(module.filtered_runs(db, {"status": ["BLOCKED"]})[0]["run_id"], "r1")
            detail = module.run_detail(db, "r1")
            self.assertEqual(detail["run"]["task_id"], "task-1")
            self.assertEqual(len(detail["timeline"]), 1)
            self.assertEqual(detail["logs"][0]["agent"], "aghuse_backend")
            self.assertEqual(module.attention(db)["items"][0]["kind"], "BLOCKED")
            self.assertEqual(module.models_usage(db)["calls"], 1)
            self.assertEqual(module.models_usage(db, {"model": ["model-x"]})["calls"], 1)
            self.assertEqual(module.models_usage(db, {"model": ["other"]})["calls"], 0)
            self.assertEqual(module.metrics_series(db)["date_quality"], "UNKNOWN/NOT_OBSERVED")
            self.assertEqual(module.metrics_series(db)["series"][0]["calls"], 1)
            self.assertEqual(module.agent_detail(db, "aghuse_backend")["usage"]["calls"], 1)
            self.assertEqual(module.evidence(db, {"q": ["TEST"]})["items"][0]["category"], "TEST")
            self.assertIn("graph", module.evidence(db, {"q": ["TEST"]}))

    def test_task_payload_rejects_missing_or_invalid_values(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_payload", ROOT / "scripts/jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
        clean, error = module.task_payload({"task_id": "", "query": "x"})
        self.assertIsNone(clean); self.assertIn("obrigatórios", error)
        clean, error = module.task_payload({"task_id": "t1", "query": "corrigir", "risk_class": "INVALID"})
        self.assertIsNone(clean); self.assertIn("risk_class", error)
        clean, error = module.task_payload({"task_id": "t1", "query": "corrigir"})
        self.assertIsNone(error); self.assertEqual(clean["complexity"], "LOCALIZED")

    def test_settings_draft_requires_confirmation_to_apply_and_rollback(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_settings", ROOT / "scripts/jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            module.SETTINGS_STORE = base / "settings.jsonl"
            module.ROOT = base
            draft = module.create_settings_draft({"limits": {"max_credits": 3}})
            with self.assertRaises(ValueError): module.apply_settings_revision(draft["revision_id"], {})
            applied = module.apply_settings_revision(draft["revision_id"], {"confirm": True, "reason": "teste"})
            self.assertEqual(applied["status"], "APPLIED")
            rolled = module.rollback_settings_revision(draft["revision_id"], {"confirm": True, "reason": "teste"})
            self.assertEqual(rolled["status"], "ROLLED_BACK")

    def test_dashboard_html_has_operational_and_accessible_shell(self):
        spec = importlib.util.spec_from_file_location("jarvis_dashboard_html", ROOT / "scripts/jarvis_dashboard.py")
        module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)
        self.assertIn('<html lang="pt-BR">', module.HTML)
        self.assertIn('name="viewport"', module.HTML)
        self.assertIn("Chat operacional", module.HTML)
        self.assertIn("Busca global", module.HTML)
        self.assertIn("Command Palette", module.HTML)
        self.assertIn("aria-live", module.HTML)
        self.assertIn("event.ctrlKey", module.HTML)


if __name__ == "__main__":
    unittest.main()
