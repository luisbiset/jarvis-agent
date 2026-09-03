from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
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
            "reasoning_class": None,
            "budget_justification": None,
            "runs_dir": Path(root),
        }
        values.update(overrides)
        return RUNTIME.initialize(argparse.Namespace(**values))

    def transition(self, run_dir: str, target: str, **overrides):
        values = {
            "run_dir": run_dir, "to": target, "reason": f"to {target}", "stop_reason": None,
            "gate_decision": None, "gate_reason_code": None, "gate_reason_detail": None,
            "rework_origin": None, "rework_reason": None,
        }
        values.update(overrides)
        return RUNTIME.transition(argparse.Namespace(**values))

    def test_initializes_append_only_run_and_budget(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            state = result["state"]
            self.assertEqual(state["current_state"], "NEW")
            self.assertEqual(state["budget"]["max_agents"], 2)
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
            state = result["state"]
            RUNTIME._register_agent(state, "aghuse_frontend", None)
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME._register_agent(state, "aghuse_auditor_do_diff", None)

    def test_handoff_requires_requirement_mapping_and_not_executed(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            handoff = RUNTIME.handoff_template(result["state"])
            handoff["requirement_ids"] = ["RN01"]
            handoff["files"] = [{"path": "A.java", "purpose": "fix", "requirement_ids": ["RN02"], "owner": "dev"}]
            errors = RUNTIME.validate_handoff_data(handoff)
            self.assertTrue(any("RN02" in error for error in errors))
            self.assertIn("not_executed", handoff["validations"])

    def technical_spec(self, workspace: Path):
        source = workspace / "src" / "Rule.java"
        test = workspace / "tests" / "RuleTest.java"
        source.parent.mkdir(parents=True, exist_ok=True)
        test.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("class Rule { void decide() {} }\n", encoding="utf-8")
        test.write_text("class RuleTest { void preservesRegression() {} }\n", encoding="utf-8")
        evidence = lambda description, path, symbol: {
            "description": description, "path": path, "symbol": symbol, "reason": "símbolo central"
        }
        return {
            "summary": "A regra passou a preservar execuções distintas.",
            "previous_behavior": "Execuções distintas eram consolidadas.",
            "new_behavior": "A decisão mantém execuções distintas.",
            "changed_components": [evidence("decisão principal", "src/Rule.java", "decide")],
            "execution_flow": [evidence("regra", "src/Rule.java", "Rule")],
            "decisions": [evidence("decisão localizada", "src/Rule.java", "decide")],
            "risks": [evidence("não quebrar a separação", "src/Rule.java", "decide")],
            "test_evidence": [evidence("regressão", "tests/RuleTest.java", "preservesRegression")],
            "reading_order": [],
        }

    def create_technical_handoff(self, result, workspace: Path, spec=None, **overrides):
        input_path = workspace / "technical-input.json"
        RUNTIME.write_json(input_path, spec or self.technical_spec(workspace))
        values = {
            "run_dir": result["run_dir"], "input": str(input_path),
            "workspace_root": str(workspace), "output": None,
            "handoff_tokens": 0, "duration_ms": 10,
        }
        values.update(overrides)
        return RUNTIME.create_technical_handoff(argparse.Namespace(**values))

    def test_knowledge_transfer_reuses_complexity_and_business_rule_signal(self):
        with tempfile.TemporaryDirectory() as root:
            trivial = self.initialize(root, complexity="TRIVIAL", risk_class="LOW", task_type="DOCUMENTATION")
            self.assertFalse(RUNTIME.knowledge_transfer_decision(trivial["state"])["enabled"])
        with tempfile.TemporaryDirectory() as root:
            business = self.initialize(root, task_type="BUSINESS_RULE")
            decision = RUNTIME.knowledge_transfer_decision(business["state"])
            self.assertEqual((decision["classification"], decision["handoff"], decision["teach_back_questions"]), ("BUSINESS_RULE", "FULL", 3))

    def test_knowledge_transfer_recognizes_delimited_business_rule_variants(self):
        variants = (
            "business-rule-runtime-fix",
            "localized-business-rule-fix",
            "backend_regra_negocio_ajuste",
            "correcao-regra-de-negocio-localizada",
        )
        for task_type in variants:
            with self.subTest(task_type=task_type), tempfile.TemporaryDirectory() as root:
                result = self.initialize(root, complexity="LOCALIZED", task_type=task_type)
                decision = RUNTIME.knowledge_transfer_decision(result["state"])
                self.assertEqual(
                    (decision["classification"], decision["handoff"], decision["teach_back_questions"]),
                    ("BUSINESS_RULE", "FULL", 3),
                )

    def test_knowledge_transfer_does_not_match_similar_undelimited_terms(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="LOCALIZED", task_type="business-rules-documentation")
            decision = RUNTIME.knowledge_transfer_decision(result["state"])
            self.assertEqual(
                (decision["classification"], decision["handoff"], decision["teach_back_questions"]),
                ("LOCALIZED", "SHORT", 0),
            )

    def test_technical_handoff_binds_real_evidence_and_marks_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root) / "workspace"
            result = self.initialize(root, complexity="TRANSVERSAL", task_type="BACKEND")
            spec = self.technical_spec(workspace)
            spec["execution_flow"].append({"description": "ausente", "path": "src/Missing.java", "symbol": "missing", "reason": "não localizado"})
            created = self.create_technical_handoff(result, workspace, spec)
            handoff = json.loads(Path(created["technical_handoff"]).read_text(encoding="utf-8"))
            self.assertEqual(handoff["evidence_status"], "PARTIAL")
            self.assertEqual(handoff["execution_flow"][-1]["evidence_status"], "UNKNOWN")
            self.assertEqual(handoff["reading_order"][0]["symbol"], "decide")
            self.assertEqual(handoff["reading_order"][-1]["symbol"], "preservesRegression")
            self.assertEqual(len(handoff["questions"]), 4)

    def test_technical_handoff_budget_persistence_and_recovery_by_task(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root) / "workspace"
            result = self.initialize(root, task_id="TASK-KT-1", complexity="TRANSVERSAL", task_type="BACKEND")
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                self.create_technical_handoff(result, workspace, handoff_tokens=4001)
            created = self.create_technical_handoff(result, workspace, handoff_tokens=120)
            recovered = RUNTIME.get_technical_handoff(argparse.Namespace(task_id="TASK-KT-1", telemetry_db=Path(result["telemetry_db"])))
            self.assertEqual(recovered["handoff_id"], created["handoff_id"])
            with sqlite3.connect(result["telemetry_db"]) as connection:
                row = connection.execute("SELECT handoff_tokens,handoff_duration_ms FROM technical_handoffs").fetchone()
            self.assertEqual(row, (120, 10))

    def test_teachback_evaluates_without_persisting_answer_and_respects_turn_budget(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root) / "workspace"
            result = self.initialize(root, complexity="TRANSVERSAL", task_type="BACKEND")
            created = self.create_technical_handoff(result, workspace)
            handoff = json.loads(Path(created["technical_handoff"]).read_text(encoding="utf-8"))
            question = handoff["questions"][0]
            partial_answer = " ".join(question["expected_concepts"][:2])
            evaluation = RUNTIME.evaluate_teachback(argparse.Namespace(
                handoff_id=created["handoff_id"], question_id=question["question_id"],
                answer=partial_answer, duration_ms=5, telemetry_db=Path(result["telemetry_db"]),
            ))
            self.assertIn(evaluation["result"], {"PARTIAL", "CORRECT"})
            with sqlite3.connect(result["telemetry_db"]) as connection:
                columns = [row[1] for row in connection.execute("PRAGMA table_info(teachback_evaluations)")]
            self.assertNotIn("answer", columns)
            for _ in range(5):
                RUNTIME.evaluate_teachback(argparse.Namespace(
                    handoff_id=created["handoff_id"], question_id=question["question_id"],
                    answer="sem correspondência", duration_ms=0, telemetry_db=Path(result["telemetry_db"]),
                ))
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.evaluate_teachback(argparse.Namespace(
                    handoff_id=created["handoff_id"], question_id=question["question_id"],
                    answer="nova tentativa", duration_ms=0, telemetry_db=Path(result["telemetry_db"]),
                ))

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

    def test_invocations_are_individual_and_usage_is_aggregated_in_sqlite(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            start = RUNTIME.invocation_start(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=None, agent="aghuse_qa", stage="VALIDATING",
                model=None, reasoning_effort="medium", parallel_batch="validation-1",
                budget_justification=None,
            ))
            RUNTIME.finding(argparse.Namespace(
                run_dir=result["run_dir"], finding_id=None, invocation_id=start["invocation_id"],
                category="REGRESSION", severity="CRITICAL", actioned=True,
                evidence_ref="tests/FakeTest.java#failure",
            ))
            RUNTIME.invocation_finish(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=start["invocation_id"], status="OK",
                agent_result="FOUND_ISSUE", input_tokens=100, cached_input_tokens=40,
                output_tokens=20, credits=1.5, retry_count=0, blocker=None,
            ))
            state = json.loads(Path(result["run_dir"], "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["metrics"]["agent_invocation_count"], 1)
            self.assertEqual(state["metrics"]["cached_input_tokens"], 40)
            self.assertEqual(state["routing"]["parallel_batches"], 1)
            with sqlite3.connect(result["telemetry_db"]) as connection:
                row = connection.execute(
                    "SELECT model,reasoning_effort,findings_count,critical_findings_count FROM agent_invocations"
                ).fetchone()
            self.assertEqual(row, ("gpt-5.6-terra", "medium", 1, 1))

    def test_rework_and_human_gate_reason_are_measured(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            run_dir = result["run_dir"]
            self.transition(run_dir, "PLAN_APPROVED")
            self.transition(run_dir, "IMPLEMENTING")
            self.transition(run_dir, "VALIDATING")
            self.transition(run_dir, "IMPLEMENTING", rework_origin="QA", rework_reason="REGRESSION")
            self.transition(run_dir, "VALIDATING")
            self.transition(run_dir, "REVIEW_READY")
            self.transition(run_dir, "HUMAN_GATE")
            state = self.transition(run_dir, "DONE", gate_decision="APPROVED")
            self.assertEqual(state["metrics"]["rework_cycles"], 1)
            self.assertFalse(state["metrics"]["first_pass_success"])
            self.assertTrue(state["metrics"]["human_gate_pass_on_first_attempt"])
            self.assertEqual(state["gate_reason_code"], "APPROVED_AS_PLANNED")
            self.assertIsNotNone(state["finished_at"])

    def test_gate_change_request_requires_reason_code(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            run_dir = result["run_dir"]
            self.transition(run_dir, "PLAN_APPROVED")
            self.transition(run_dir, "IMPLEMENTING")
            self.transition(run_dir, "VALIDATING")
            self.transition(run_dir, "REVIEW_READY")
            self.transition(run_dir, "HUMAN_GATE")
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                self.transition(
                    run_dir, "IMPLEMENTING", gate_decision="CHANGES_REQUESTED",
                    rework_origin="HUMAN", rework_reason="IMPLEMENTATION",
                )

    def test_dashboard_and_exports_use_historical_database(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            dashboard = RUNTIME.dashboard(argparse.Namespace(
                runs_dir=Path(root), telemetry_db=Path(result["telemetry_db"])
            ))
            self.assertEqual(dashboard["total_runs"], 1)
            json_output = Path(root, "export.json")
            exported = RUNTIME.export_telemetry(argparse.Namespace(
                telemetry_db=Path(result["telemetry_db"]), format="json", output=str(json_output)
            ))
            self.assertEqual(exported["rows"]["runs"], 1)
            self.assertIn("agent_invocations", json.loads(json_output.read_text(encoding="utf-8"))["tables"])

    def test_routing_and_release_evals_support_version_comparison(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root)
            routed = RUNTIME.route(argparse.Namespace(
                run_dir=result["run_dir"], routing_outcome="UNDER_ROUTED",
                agents_planned=["aghuse_backend", "aghuse_qa"], agents_skipped=["aghuse_qa"],
                agents_rejected_by_budget=None, unnecessary_agents=None, missing_agents=["aghuse_qa"],
            ))
            self.assertEqual(routed["missing_agents"], ["aghuse_qa"])
            evaluation = RUNTIME.release_eval(argparse.Namespace(
                telemetry_db=Path(result["telemetry_db"]), eval_id=None, jarvis_version=None,
                config_hash=None, routing_score=.8, over_routing_score=.9,
                under_routing_score=.7, sequence_score=1.0, source_ref="evals/result-fake.json",
            ))
            comparison = RUNTIME.compare_releases(argparse.Namespace(
                telemetry_db=Path(result["telemetry_db"])
            ))
            self.assertEqual(evaluation["routing_score"], .8)
            self.assertEqual(len(comparison["releases"]), 1)
            self.assertEqual(len(comparison["eval_results"]), 1)
            with sqlite3.connect(result["telemetry_db"]) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM routing_snapshots").fetchone()[0], 1)

    def test_v3_reasoning_scoring_boundaries_and_incomplete_fallback(self):
        base = {
            "task_type": "DOCUMENTATION", "estimated_files": 1, "estimated_modules": 1,
            "architectural": False, "production_critical": False, "database_migration": False,
            "security_sensitive": False, "tests_required": False,
            "ambiguity_score": 0.0, "complexity_score": 0.0,
        }
        self.assertEqual(RUNTIME.reasoning_decision(base)["level"], "INSTANT")
        medium = {**base, "complexity_score": 4.0}
        self.assertEqual(RUNTIME.reasoning_decision(medium)["level"], "MEDIUM")
        high = {**base, "architectural": True, "production_critical": True, "complexity_score": 4.0}
        self.assertEqual(RUNTIME.reasoning_decision(high)["level"], "HIGH")
        incomplete = {**base, "task_type": "GENERAL", "estimated_files": 0, "estimated_modules": 0}
        self.assertEqual(RUNTIME.reasoning_decision(incomplete)["level"], "MEDIUM")
        incomplete_backend = {**incomplete, "task_type": "BACKEND"}
        self.assertEqual(RUNTIME.reasoning_decision(incomplete_backend)["level"], "MEDIUM")

    def test_v3_routes_model_reasoning_and_context_together(self):
        base = {
            "task_type": "DOCUMENTATION", "estimated_files": 1, "estimated_modules": 1,
            "architectural": False, "production_critical": False, "database_migration": False,
            "security_sensitive": False, "tests_required": False,
            "ambiguity_score": 0.0, "complexity_score": 0.0,
        }
        instant = RUNTIME.reasoning_decision(base)
        medium = RUNTIME.reasoning_decision({**base, "complexity_score": 4.0})
        high = RUNTIME.reasoning_decision({**base, "architectural": True, "production_critical": True, "complexity_score": 4.0})
        self.assertEqual((instant["model"], instant["reasoning_effort"], instant["context_budget"]), ("gpt-5.6-luna", "low", "SMALL"))
        self.assertEqual((medium["model"], medium["reasoning_effort"], medium["context_budget"]), ("gpt-5.6-terra", "medium", "MEDIUM"))
        self.assertEqual((high["model"], high["reasoning_effort"], high["context_budget"]), ("gpt-5.6-sol", "high", "LARGE"))

    def test_v3_rejects_model_override_and_retry_without_progress(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, reasoning_class=None, task_type="BACKEND", complexity_score=4.0)
            state = result["state"]
            state["budget"]["max_parallel_agents"] = 2
            RUNTIME.write_json(Path(result["run_dir"], "state.json"), state)
            common = dict(
                run_dir=result["run_dir"], invocation_id=None, agent="aghuse_backend", stage="IMPLEMENTING",
                reasoning_effort=None, attempt_number=None, task_type=None, parent_execution_id=None,
                child_depth=0, parallel_batch=None, budget_justification=None,
            )
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_start(argparse.Namespace(model="gpt-5.6-sol", **common))
            first = RUNTIME.invocation_start(argparse.Namespace(model=None, **common))
            self.assertIsNone(first["model_effective"])
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_start(argparse.Namespace(model=None, **common))
            retry = RUNTIME.invocation_start(argparse.Namespace(model=None, progress_event="PLAN_CHANGED", **common))
            self.assertEqual(retry["attempt_number"], 2)

    def test_v3_applies_agent_cap_and_records_only_observed_effective_model(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="TRANSVERSAL", risk_class="HIGH", reasoning_class=None, task_type="ARCHITECTURE", architectural=True, production_critical=True, complexity_score=4.0)
            started = RUNTIME.invocation_start(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=None, agent="sfa_tests", stage="VALIDATING",
                model=None, reasoning_effort=None, attempt_number=None, task_type="TEST",
                parent_execution_id=None, child_depth=0, progress_event=None, parallel_batch=None,
                budget_justification=None,
            ))
            self.assertEqual((started["model_requested"], started["reasoning_level"], started["context_budget"]), ("gpt-5.6-terra", "MEDIUM", "MEDIUM"))
            self.assertIsNone(started["model_effective"])
            RUNTIME.invocation_finish(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=started["invocation_id"], status="OK",
                agent_result="USEFUL", model_effective="gpt-5.6-terra", reasoning_effort_effective="medium",
                input_tokens=20, cached_input_tokens=5, output_tokens=10, credits=0,
                retry_count=0, files_read=1, files_changed=0, tool_calls=1, tests_run=1,
                tests_passed=1, tests_failed=0, review_findings=0, success=True,
                termination_reason="SUCCESS", blocker=None,
            ))
            with sqlite3.connect(result["telemetry_db"]) as connection:
                row = connection.execute("SELECT model_requested,model_effective,context_budget FROM execution_attempts").fetchone()
            self.assertEqual(row, ("gpt-5.6-terra", "gpt-5.6-terra", "MEDIUM"))

    def test_v3_critical_has_high_floor(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="CRITICAL", risk_class="CRITICAL", reasoning_class=None, task_type="GENERAL", complexity_score=0.0)
            self.assertEqual(result["state"]["reasoning"]["current_level"], "HIGH")
            self.assertEqual(result["state"]["reasoning"]["requested_model"], "gpt-5.6-sol")

    def test_v3_rejects_effort_override_and_unverified_escalation(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="TRANSVERSAL", reasoning_class=None, task_type="BACKEND", complexity_score=4.0)
            common = dict(
                run_dir=result["run_dir"], invocation_id=None, agent="aghuse_backend", stage="IMPLEMENTING",
                model=None, attempt_number=None, task_type=None, parent_execution_id=None,
                child_depth=0, parallel_batch=None, budget_justification=None,
            )
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_start(argparse.Namespace(reasoning_effort="high", **common))
            started = RUNTIME.invocation_start(argparse.Namespace(reasoning_effort="medium", **common))
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_finish(argparse.Namespace(
                    run_dir=result["run_dir"], invocation_id=started["invocation_id"], status="FAILED",
                    agent_result="BLOCKED", input_tokens=0, cached_input_tokens=0, output_tokens=0,
                    credits=0, retry_count=0, files_read=0, files_changed=0, tool_calls=0,
                    tests_run=0, tests_passed=0, tests_failed=0, review_findings=0,
                    success=False, termination_reason="TEST_FAILURE", blocker="ignored free text",
                ))
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.evaluate_attempt(argparse.Namespace(
                    run_dir=result["run_dir"], success=False, escalation_reason="TEST_FAILURE",
                    previous_execution_id="inv-inexistente", changed_files=[], tests_failed=1,
                    failed_hypotheses_count=0,
                ))

    def test_v3_medium_escalates_once_to_high_with_compact_context(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, reasoning_class=None, task_type="BACKEND", complexity_score=4.0)
            started = RUNTIME.invocation_start(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=None, agent="aghuse_backend", stage="IMPLEMENTING",
                model=None, reasoning_effort=None, attempt_number=None, task_type=None,
                parent_execution_id=None, child_depth=0, parallel_batch=None, budget_justification=None,
            ))
            RUNTIME.invocation_finish(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=started["invocation_id"], status="FAILED",
                agent_result="BLOCKED", input_tokens=10, cached_input_tokens=0, output_tokens=5,
                credits=0.5, retry_count=0, files_read=2, files_changed=1, tool_calls=2,
                tests_run=1, tests_passed=0, tests_failed=1, review_findings=0,
                success=False, termination_reason="TEST_FAILURE", blocker="controlled failure",
            ))
            escalation = RUNTIME.evaluate_attempt(argparse.Namespace(
                run_dir=result["run_dir"], success=False, escalation_reason="TEST_FAILURE",
                previous_execution_id=started["invocation_id"], changed_files=["src/Foo.java"],
                tests_failed=1, failed_hypotheses_count=1,
            ))
            self.assertTrue(escalation["escalate"])
            self.assertEqual(escalation["reasoning_level"], "HIGH")
            self.assertEqual(escalation["reasoning_effort"], "high")
            self.assertEqual(escalation["model"], "gpt-5.6-sol")
            self.assertEqual(escalation["context_budget"], "LARGE")
            self.assertTrue(Path(escalation["context"]).is_file())
            denied = RUNTIME.evaluate_attempt(argparse.Namespace(
                run_dir=result["run_dir"], success=False, escalation_reason="TEST_FAILURE",
                previous_execution_id=started["invocation_id"], changed_files=[], tests_failed=1,
                failed_hypotheses_count=0,
            ))
            self.assertFalse(denied["escalate"])
            self.assertEqual(denied["termination_reason"], "BUDGET_EXHAUSTED")

    def test_v3_persists_one_metric_row_per_attempt(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, reasoning_class=None, task_type="TEST", complexity_score=4.0)
            started = RUNTIME.invocation_start(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=None, agent="sfa_tests", stage="VALIDATING",
                model=None, reasoning_effort=None, attempt_number=None, task_type="TEST",
                parent_execution_id=None, child_depth=0, parallel_batch=None, budget_justification=None,
            ))
            RUNTIME.invocation_finish(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=started["invocation_id"], status="OK",
                agent_result="USEFUL", input_tokens=20, cached_input_tokens=5, output_tokens=10,
                credits=0.7, retry_count=0, files_read=3, files_changed=1, tool_calls=4,
                tests_run=2, tests_passed=2, tests_failed=0, review_findings=0,
                success=True, termination_reason="SUCCESS", blocker=None,
            ))
            with sqlite3.connect(result["telemetry_db"]) as connection:
                row = connection.execute(
                    "SELECT attempt_number,initial_reasoning,effective_reasoning,total_tokens,files_changed,tests_passed,success,termination_reason,child_depth FROM execution_attempts"
                ).fetchone()
            self.assertEqual(row, (1, "MEDIUM", "MEDIUM", 30, 1, 2, 1, "SUCCESS", 0))

    def test_v3_rejects_child_depth_and_attempt_over_budget(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, reasoning_class=None, task_type="BACKEND", complexity_score=4.0)
            common = dict(
                run_dir=result["run_dir"], invocation_id=None, agent="aghuse_backend", stage="IMPLEMENTING",
                model=None, reasoning_effort=None, task_type=None, parent_execution_id=None,
                parallel_batch=None, budget_justification=None,
            )
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_start(argparse.Namespace(attempt_number=1, child_depth=4, **common))
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_start(argparse.Namespace(attempt_number=4, child_depth=0, **common))

    def test_v3_attempt_budget_separates_agents_from_global_retries(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="TRANSVERSAL", reasoning_class=None, task_type="BACKEND", complexity_score=4.0)
            state = result["state"]
            state["budget"]["max_parallel_agents"] = 10
            state["budget"]["max_model_calls"] = state["budget"]["hard_max_model_calls"]
            RUNTIME.write_json(Path(result["run_dir"], "state.json"), state)
            attempts = []
            for agent in ("aghuse_backend", "aghuse_database", "aghuse_tests"):
                started = RUNTIME.invocation_start(argparse.Namespace(
                    run_dir=result["run_dir"], invocation_id=None, agent=agent, stage="IMPLEMENTING",
                    model=None, reasoning_effort=None, attempt_number=None, task_type=None,
                    parent_execution_id=None, child_depth=0, parallel_batch=None,
                    budget_justification=None,
                ))
                attempts.append(started["attempt_number"])
            self.assertEqual(attempts, [1, 1, 1])
            fourth = RUNTIME.invocation_start(argparse.Namespace(
                    run_dir=result["run_dir"], invocation_id=None, agent="aghuse_qa", stage="VALIDATING",
                    model=None, reasoning_effort=None, attempt_number=None, task_type=None,
                    parent_execution_id=None, child_depth=0, parallel_batch=None,
                    budget_justification=None,
                ))
            self.assertEqual(fourth["attempt_number"], 1)
            for agent in ("aghuse_backend", "aghuse_database", "aghuse_tests"):
                retry = RUNTIME.invocation_start(argparse.Namespace(
                    run_dir=result["run_dir"], invocation_id=None, agent=agent, stage="IMPLEMENTING",
                    model=None, reasoning_effort=None, attempt_number=None, task_type=None,
                    parent_execution_id=None, child_depth=0, parallel_batch=None,
                    budget_justification=None, progress_event="NEW_TEST_RESULT",
                ))
                self.assertEqual(retry["attempt_number"], 2)
            with self.assertRaises(RUNTIME.RuntimeErrorSafe):
                RUNTIME.invocation_start(argparse.Namespace(
                    run_dir=result["run_dir"], invocation_id=None, agent="aghuse_qa", stage="VALIDATING",
                    model=None, reasoning_effort=None, attempt_number=None, task_type=None,
                    parent_execution_id=None, child_depth=0, parallel_batch=None,
                    budget_justification=None, progress_event="NEW_TEST_RESULT",
                ))

    def test_v31_applies_model_call_and_agent_limits_by_complexity(self):
        expected = {
            "TRIVIAL": (1, 1),
            "LOCALIZED": (2, 3),
            "TRANSVERSAL": (4, 5),
            "CRITICAL": (6, 6),
        }
        with tempfile.TemporaryDirectory() as root:
            for complexity, (agents, calls) in expected.items():
                run_root = Path(root, complexity.lower())
                result = self.initialize(run_root, complexity=complexity, risk_class="LOW", task_type="ANALYSIS", estimated_files=2, estimated_modules=1, complexity_score=4.0)
                self.assertEqual((result["state"]["budget"]["max_agents"], result["state"]["budget"]["max_model_calls"]), (agents, calls))

    def test_v31_fast_path_is_explicit_and_excludes_sensitive_work(self):
        with tempfile.TemporaryDirectory() as root:
            fast = self.initialize(Path(root, "fast"), complexity="TRIVIAL", risk_class="LOW", task_type="DOCUMENTATION", estimated_files=1, estimated_modules=1)
            self.assertEqual(fast["state"]["execution_path"], "FAST_PATH")
            sensitive = self.initialize(Path(root, "sensitive"), complexity="TRIVIAL", risk_class="LOW", task_type="SECURITY", estimated_files=1, estimated_modules=1, security_sensitive=True)
            self.assertEqual(sensitive["state"]["execution_path"], "STANDARD")

    def test_v31_observes_context_and_cost_limits_without_blocking(self):
        with tempfile.TemporaryDirectory() as root:
            state = self.initialize(root, complexity="TRIVIAL", risk_class="LOW", task_type="DOCUMENTATION", estimated_files=1, estimated_modules=1)["state"]
            warnings = RUNTIME.observe_usage(state, {
                "files_read": 5, "input_tokens": 26000, "cached_input_tokens": 0,
                "tool_calls": 9, "credits": 6.0,
            })
            self.assertIn("CONTEXT_LIMIT_OBSERVED:files", warnings)
            self.assertIn("COST_HARD_LIMIT_OBSERVED", warnings)
            self.assertEqual(state["context_usage"]["mode"], "OBSERVE_ONLY")
            self.assertEqual(state["cost_budget"]["status"], "HARD_LIMIT_OBSERVED")

    def test_v31_report_cost_aggregates_agent_cache_and_retries(self):
        with tempfile.TemporaryDirectory() as root:
            result = self.initialize(root, complexity="LOCALIZED", task_type="BACKEND", complexity_score=4.0)
            started = RUNTIME.invocation_start(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=None, agent="aghuse_backend", stage="IMPLEMENTING",
                model=None, reasoning_effort=None, attempt_number=None, task_type=None,
                parent_execution_id=None, child_depth=0, progress_event=None, parallel_batch=None,
                budget_justification=None,
            ))
            RUNTIME.invocation_finish(argparse.Namespace(
                run_dir=result["run_dir"], invocation_id=started["invocation_id"], status="OK",
                agent_result="USEFUL", model_effective="gpt-5.6-terra", reasoning_effort_effective="medium",
                input_tokens=100, cached_input_tokens=40, output_tokens=20, credits=2.5,
                retry_count=0, files_read=2, files_changed=1, tool_calls=3, tests_run=1,
                tests_passed=1, tests_failed=0, review_findings=0, success=True,
                termination_reason="SUCCESS", blocker=None,
            ))
            report = RUNTIME.report_cost(argparse.Namespace(
                telemetry_db=Path(result["telemetry_db"]), runs_dir=Path(root),
                run_id=result["state"]["run_id"], last=20, group_by="agent",
            ))
            self.assertEqual(report["totals"]["credits"], 2.5)
            self.assertEqual(report["totals"]["uncached_input_tokens"], 60)
            self.assertEqual(report["by_agent"]["aghuse_backend"]["cache_hit_ratio"], 0.4)


if __name__ == "__main__":
    unittest.main()
