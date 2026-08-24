from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "jarvis_runtime.py"
SPEC = importlib.util.spec_from_file_location("jarvis_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class JarvisRuntimeTest(unittest.TestCase):
    def initialize(self, root: str, **overrides):
        values = {
            "task_id": "TASK-FAKE-1",
            "complexity": "LOCALIZED",
            "risk_class": "MEDIUM",
            "operational_mode": "ASSISTED_AUTOPILOT",
            "reasoning_class": "NORMAL",
            "budget_justification": None,
            "runs_dir": Path(root),
        }
        values.update(overrides)
        return RUNTIME.initialize(argparse.Namespace(**values))

    def test_initializes_append_only_run_and_budget(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            state = result["state"]
            self.assertEqual(state["current_state"], "NEW")
            self.assertEqual(state["budget"]["max_agents"], 3)
            events = Path(result["run_dir"], "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(events), 1)

    def test_transversal_cannot_skip_formal_plan(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="TRANSVERSAL")
            args = argparse.Namespace(
                run_dir=result["run_dir"], to="PLAN_APPROVED", reason="skip", stop_reason=None, gate_decision=None
            )
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.transition(args)

    def test_read_only_mode_cannot_implement(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, operational_mode="READ_ONLY_AUDIT")
            first = argparse.Namespace(
                run_dir=result["run_dir"], to="PLAN_APPROVED", reason="direct", stop_reason=None, gate_decision=None
            )
            RUNTIME.transition(first)
            second = argparse.Namespace(
                run_dir=result["run_dir"], to="IMPLEMENTING", reason="write", stop_reason=None, gate_decision=None
            )
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.transition(second)

    def test_budget_requires_justification(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="TRIVIAL", risk_class="LOW")
            common = {
                "run_dir": result["run_dir"], "stage": "NEW", "status": "OK", "reasoning_class": "FAST",
                "started_at": None, "finished_at": None, "input_refs": [], "output_artifact": None,
                "files_read": [], "files_changed": [], "validations": [], "duration_ms": 0,
                "token_or_credit_cost": 0, "retry_count": 0, "blocker": None, "budget_justification": None,
            }
            RUNTIME.record(argparse.Namespace(agent="aghuse_frontend", **common))
            RUNTIME.record(argparse.Namespace(agent="aghuse_auditor_do_diff", **common))
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.record(argparse.Namespace(agent="aghuse_backend", **common))

    def test_handoff_requires_requirement_mapping_and_not_executed(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            handoff = RUNTIME.handoff_template(result["state"])
            handoff["requirement_ids"] = ["RN01"]
            handoff["files"] = [{"path": "A.java", "purpose": "fix", "requirement_ids": ["RN02"], "owner": "dev"}]
            errors = RUNTIME.validate_handoff_data(handoff)
            self.assertTrue(any("RN02" in error for error in errors))
            self.assertIn("not_executed", handoff["validations"])

    def test_sensitive_metadata_is_refused(self):
        with self.assertRaises(RUNTIME.RuntimeErrorSafe):
            RUNTIME.assert_safe_metadata({"api_key": "not-a-real-value"})

    def test_context_pack_contains_refs_not_source_content(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            args = argparse.Namespace(
                run_dir=result["run_dir"], kind="contract", baseline="abc123", ref=["src/Foo.java#method"]
            )
            created = RUNTIME.context_pack(args)
            data = json.loads(Path(created["context_pack"]).read_text(encoding="utf-8"))
            self.assertEqual(data["content_policy"], "references_and_hashes_only")
            self.assertNotIn("content", data)


if __name__ == "__main__":
    unittest.main()
