#!/usr/bin/env python3
"""Runtime local do Jarvis V3: adaptive reasoning, fluxo e telemetria segura."""

from __future__ import annotations

import argparse
import csv
import fcntl
import functools
import hashlib
import json
import re
import secrets
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "contracts/version.json"
REASONING_POLICY_PATH = ROOT / "contracts/reasoning-policy.json"
KNOWLEDGE_TRANSFER_POLICY_PATH = ROOT / "contracts/knowledge-transfer-policy.json"
DEFAULT_RUNS_DIR = ROOT / ".jarvis/runs"
DEFAULT_TELEMETRY_DB = ROOT / ".jarvis/telemetry/jarvis.db"
COMPLEXITIES = ("TRIVIAL", "LOCALIZED", "TRANSVERSAL", "CRITICAL")
RISKS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
MODES = ("COPILOT", "ASSISTED_AUTOPILOT", "READ_ONLY_AUDIT")
REASONING = ("FAST", "NORMAL", "DEEP")
REASONING_LEVELS = ("INSTANT", "MEDIUM", "HIGH")
REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
CONTEXT_BUDGETS = ("SMALL", "MEDIUM", "LARGE")
PROGRESS_EVENTS = ("NEW_TEST_RESULT", "NEW_RELEVANT_SYMBOL", "HYPOTHESIS_DISCARDED", "PLAN_CHANGED", "MODEL_ESCALATED")
STATES = ("NEW", "DISCOVERY", "PLAN_READY", "PLAN_APPROVED", "IMPLEMENTING", "VALIDATING", "REVIEW_READY", "HUMAN_GATE", "HOMOLOGATION_READY", "DONE", "BLOCKED")
STOP_REASONS = ("AMBIGUOUS_REQUIREMENT", "SHARED_CONTRACT_OUT_OF_SCOPE", "TEST_CONTRADICTION", "EXTERNAL_AUTHORIZATION_REQUIRED", "INSUFFICIENT_CONTEXT", "VALIDATION_NOT_REPRODUCIBLE", "SPECIALIST_DIVERGENCE", "NEEDS_EXPLANATION")
GATE_DECISIONS = ("APPROVED", "CHANGES_REQUESTED", "REJECTED")
GATE_REASON_CODES = ("APPROVED_AS_PLANNED", "WRONG_REQUIREMENT", "REGRESSION", "INSUFFICIENT_TEST", "OUT_OF_SCOPE", "BAD_IMPLEMENTATION", "BAD_EXPLANATION", "OTHER")
AGENT_RESULTS = ("USEFUL", "NO_FINDING", "FOUND_ISSUE", "BLOCKED", "DUPLICATE_FINDING", "INCONCLUSIVE")
ROUTING_OUTCOMES = ("CORRECT", "OVER_ROUTED", "UNDER_ROUTED", "UNKNOWN")
REWORK_ORIGINS = ("QA", "AUDITOR", "REVIEWER", "HUMAN", "TEST", "BUILD")
REWORK_REASONS = ("REQUIREMENT", "IMPLEMENTATION", "REGRESSION", "TEST", "SCOPE", "SECURITY", "DATABASE", "UI", "CONTRACT")
FINDING_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
ESCALATION_REASONS = ("TEST_FAILURE", "REPEATED_TOOL_FAILURE", "RESULT_INCONSISTENCY", "UNPLANNED_ARCHITECTURE", "SCOPE_EXPANDED", "CRITICAL_REVIEW_FINDING")
TERMINATION_REASONS = ("SUCCESS", "BUDGET_EXHAUSTED", "TEST_FAILURE", "TOOL_FAILURE", "HUMAN_REVIEW_REQUIRED")
BUDGETS = {"TRIVIAL": (1, 1), "LOCALIZED": (2, 1), "TRANSVERSAL": (4, 2), "CRITICAL": (6, 2)}
REQUIRED_REVIEWERS = {"LOW": [], "MEDIUM": ["technical_qa_or_diff_auditor"], "HIGH": ["technical_qa", "diff_auditor", "system_reviewer"], "CRITICAL": ["technical_qa", "diff_auditor", "system_reviewer", "human_explainability_gate"]}
TRANSITIONS = {
    "NEW": {"DISCOVERY", "PLAN_APPROVED", "BLOCKED"}, "DISCOVERY": {"PLAN_READY", "BLOCKED"},
    "PLAN_READY": {"PLAN_APPROVED", "DISCOVERY", "BLOCKED"}, "PLAN_APPROVED": {"IMPLEMENTING", "VALIDATING", "BLOCKED"},
    "IMPLEMENTING": {"VALIDATING", "BLOCKED"}, "VALIDATING": {"REVIEW_READY", "IMPLEMENTING", "BLOCKED"},
    "REVIEW_READY": {"HUMAN_GATE", "IMPLEMENTING", "BLOCKED"}, "HUMAN_GATE": {"HOMOLOGATION_READY", "DONE", "IMPLEMENTING", "BLOCKED"},
    "HOMOLOGATION_READY": {"DONE", "IMPLEMENTING", "BLOCKED"}, "DONE": set(),
    "BLOCKED": {"DISCOVERY", "PLAN_READY", "PLAN_APPROVED", "IMPLEMENTING", "VALIDATING"},
}
SENSITIVE_KEY = re.compile(r"(?i)(api.?key|password|passwd|secret|credential|authorization|cookie|patient|paciente)")
SENSITIVE_VALUE = re.compile(r"(?i)(bearer\s+[a-z0-9._-]+|https?://[^\s]*(?:intra|saude|local)[^\s]*|api[_-]?key\s*[=:])")
DEVELOPMENT_TASK_TYPES = {"BACKEND", "FRONTEND", "DATABASE", "TEST", "SECURITY", "ARCHITECTURE", "INTEGRATION"}
KNOWLEDGE_TRANSFER_CLASSES = ("TRIVIAL", "LOCALIZED", "BUSINESS_RULE", "TRANSVERSAL", "CRITICAL")
EVIDENCE_STATUSES = ("CONFIRMED", "PARTIAL", "UNKNOWN")
TEACHBACK_RESULTS = ("CORRECT", "PARTIAL", "INCORRECT")


class RuntimeErrorSafe(RuntimeError):
    """Erro operacional sem stack trace por padrão."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeErrorSafe(f"timestamp ISO-8601 inválido: {value}") from exc


def elapsed_ms(started_at: str, finished_at: str) -> int:
    result = round((parse_time(finished_at) - parse_time(started_at)).total_seconds() * 1000)
    if result < 0:
        raise RuntimeErrorSafe("finished_at não pode ser anterior a started_at")
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeErrorSafe(f"JSON inválido ou inacessível em {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeErrorSafe(f"objeto JSON esperado em {path}")
    return value


def load_reasoning_policy() -> dict[str, Any]:
    policy = load_json(REASONING_POLICY_PATH)
    required = {"policy_version", "default_level", "levels", "agent_caps", "thresholds", "weights", "limits", "escalation", "context_limits", "model_call_limits", "cost_limits", "budget"}
    missing = required - policy.keys()
    if missing:
        raise RuntimeErrorSafe(f"política de reasoning incompleta: {sorted(missing)}")
    if policy["default_level"] not in REASONING_LEVELS:
        raise RuntimeErrorSafe("default_level inválido na política de reasoning")
    instant = policy["thresholds"].get("instant_max_score")
    medium = policy["thresholds"].get("medium_max_score")
    if not isinstance(instant, int) or not isinstance(medium, int) or instant < 0 or medium <= instant:
        raise RuntimeErrorSafe("thresholds inválidos na política de reasoning")
    if policy["budget"].get("max_attempts", 0) < 1 or policy["budget"].get("max_child_depth", 0) < 0 or policy["budget"].get("hard_max_model_calls", 0) < 1 or policy["budget"].get("max_duration_ms", 0) < 1:
        raise RuntimeErrorSafe("budget inválido na política de reasoning")
    for level in REASONING_LEVELS:
        config = policy["levels"].get(level, {})
        if config.get("reasoning_class") not in REASONING or config.get("reasoning_effort") not in REASONING_EFFORTS or not config.get("model") or config.get("context_budget") not in CONTEXT_BUDGETS or config.get("max_input_tokens", 0) < 1:
            raise RuntimeErrorSafe(f"configuração inválida para reasoning {level}")
    context_keys = ("max_files", "max_context_tokens", "max_tool_reads", "max_raw_bytes")
    previous = {key: 0 for key in context_keys}
    for level in CONTEXT_BUDGETS:
        config = policy["context_limits"].get(level, {})
        for key in context_keys:
            value = config.get(key, 0)
            if not isinstance(value, int) or value <= 0 or value < previous[key]:
                raise RuntimeErrorSafe(f"context limit inválido ou não monotônico: {level}.{key}")
            previous[key] = value
    hard_limit = policy["budget"]["hard_max_model_calls"]
    for complexity in COMPLEXITIES:
        value = policy["model_call_limits"].get(complexity, 0)
        cost = policy["cost_limits"].get(complexity, {})
        if not isinstance(value, int) or not 1 <= value <= hard_limit:
            raise RuntimeErrorSafe(f"model call limit inválido: {complexity}")
        if cost.get("max_credits", 0) <= 0 or cost.get("max_uncached_input_tokens", 0) <= 0:
            raise RuntimeErrorSafe(f"cost limit inválido: {complexity}")
    if policy["cost_limits"].get("mode") != "OBSERVE_ONLY" or not 0 < policy["cost_limits"].get("soft_limit_ratio", 0) < 1:
        raise RuntimeErrorSafe("cost limits devem iniciar em OBSERVE_ONLY com soft_limit_ratio entre 0 e 1")
    return policy


def load_knowledge_transfer_policy() -> dict[str, Any]:
    policy = load_json(KNOWLEDGE_TRANSFER_POLICY_PATH)
    if policy.get("policy_version") != "1.0.0":
        raise RuntimeErrorSafe("policy_version inválida na transferência de conhecimento")
    levels = policy.get("levels", {})
    if set(levels) != set(KNOWLEDGE_TRANSFER_CLASSES):
        raise RuntimeErrorSafe("níveis incompletos na transferência de conhecimento")
    budget = policy.get("budget", {})
    if budget.get("max_handoff_tokens", 0) < 1 or budget.get("max_teachback_turns", 0) < 1:
        raise RuntimeErrorSafe("budget inválido na transferência de conhecimento")
    for name, config in levels.items():
        if config.get("handoff") not in {"NONE", "SHORT", "FULL"}:
            raise RuntimeErrorSafe(f"nível de handoff inválido para {name}")
        if not isinstance(config.get("teach_back_questions"), int) or config["teach_back_questions"] < 0:
            raise RuntimeErrorSafe(f"quantidade de perguntas inválida para {name}")
    return policy


def knowledge_transfer_decision(state: dict[str, Any]) -> dict[str, Any]:
    policy = load_knowledge_transfer_policy()
    raw_task_type = state.get("reasoning", {}).get("signals", {}).get("task_type", "GENERAL")
    task_type = re.sub(r"[^A-Z0-9]+", "_", str(raw_task_type).upper()).strip("_")
    delimited_task_type = f"_{task_type}_"
    business_rule = any(marker in delimited_task_type for marker in (
        "_BUSINESS_RULE_", "_REGRA_NEGOCIO_", "_REGRA_DE_NEGOCIO_",
    ))
    if state["complexity"] == "CRITICAL" or state["risk_class"] == "CRITICAL":
        classification = "CRITICAL"
    elif state["complexity"] == "TRANSVERSAL":
        classification = "TRANSVERSAL"
    elif business_rule:
        classification = "BUSINESS_RULE"
    else:
        classification = state["complexity"]
    config = policy["levels"][classification]
    return {
        "policy_version": policy["policy_version"],
        "classification": classification,
        **config,
        **policy["budget"],
    }


def task_signals_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "task_type": getattr(args, "task_type", None) or "GENERAL",
        "estimated_files": getattr(args, "estimated_files", 0) or 0,
        "estimated_modules": getattr(args, "estimated_modules", 0) or 0,
        "architectural": bool(getattr(args, "architectural", False)),
        "production_critical": bool(getattr(args, "production_critical", False)),
        "database_migration": bool(getattr(args, "database_migration", False)),
        "security_sensitive": bool(getattr(args, "security_sensitive", False)),
        "tests_required": bool(getattr(args, "tests_required", False)),
        "ambiguity_score": float(getattr(args, "ambiguity_score", 0) or 0),
        "complexity_score": float(getattr(args, "complexity_score", 0) or 0),
    }


def reasoning_decision(signals: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_reasoning_policy()
    limits, weights = policy["limits"], policy["weights"]
    ambiguity = signals["ambiguity_score"]
    complexity = signals["complexity_score"]
    if not 0 <= ambiguity <= limits["max_ambiguity_points"]:
        raise RuntimeErrorSafe(f"ambiguity_score deve estar entre 0 e {limits['max_ambiguity_points']}")
    if not 0 <= complexity <= limits["max_complexity_points"]:
        raise RuntimeErrorSafe(f"complexity_score deve estar entre 0 e {limits['max_complexity_points']}")
    if signals["estimated_files"] < 0 or signals["estimated_modules"] < 0:
        raise RuntimeErrorSafe("estimativas de arquivos e módulos não podem ser negativas")
    contributions = {
        "architectural": weights["architectural"] if signals["architectural"] else 0,
        "production_critical": weights["production_critical"] if signals["production_critical"] else 0,
        "security_sensitive": weights["security_sensitive"] if signals["security_sensitive"] else 0,
        "database_migration": weights["database_migration"] if signals["database_migration"] else 0,
        "multiple_modules": weights["multiple_modules"] if signals["estimated_modules"] >= limits["multiple_modules_min"] else 0,
        "many_files": weights["many_files"] if signals["estimated_files"] >= limits["many_files_min"] else 0,
        "tests_required": weights["tests_required"] if signals["tests_required"] else 0,
        "ambiguity": ambiguity,
        "complexity": complexity,
    }
    score = sum(contributions.values())
    thresholds = policy["thresholds"]
    no_detail = not any((signals["estimated_files"], signals["estimated_modules"], signals["architectural"], signals["production_critical"], signals["database_migration"], signals["security_sensitive"], signals["tests_required"], ambiguity, complexity))
    incomplete = no_detail and (signals["task_type"] == "GENERAL" or signals["task_type"] in DEVELOPMENT_TASK_TYPES)
    level = policy["default_level"] if incomplete else "INSTANT" if score <= thresholds["instant_max_score"] else "MEDIUM" if score <= thresholds["medium_max_score"] else "HIGH"
    level_config = policy["levels"][level]
    return {
        "policy_version": policy["policy_version"],
        "level": level,
        "reasoning_class": level_config["reasoning_class"],
        "reasoning_effort": level_config["reasoning_effort"],
        "model": level_config["model"],
        "context_budget": level_config["context_budget"],
        "max_input_tokens": level_config["max_input_tokens"],
        "score": score,
        "contributions": contributions,
        "max_attempts": policy["budget"]["max_attempts"],
        "max_child_depth": policy["budget"]["max_child_depth"],
        "max_model_calls": policy["budget"]["hard_max_model_calls"],
        "max_duration_ms": policy["budget"]["max_duration_ms"],
        "escalation_allowed": bool(policy["escalation"]["enabled"] and level == policy["escalation"]["allowed_from"]),
        "max_escalations": policy["escalation"]["max_per_task"],
        "reason": "incomplete signals: default MEDIUM" if incomplete else f"score {score:g}: {level}",
        "signals": signals,
    }


def reasoning_decide(args: argparse.Namespace) -> dict[str, Any]:
    signals = task_signals_from_args(args)
    assert_safe_metadata(signals)
    return reasoning_decision(signals)


def execution_path(complexity: str, risk_class: str, decision: dict[str, Any]) -> str:
    signals = decision["signals"]
    eligible = (
        complexity == "TRIVIAL"
        and risk_class == "LOW"
        and decision["level"] == "INSTANT"
        and signals["estimated_files"] <= 1
        and signals["estimated_modules"] <= 1
        and not any(signals[key] for key in ("architectural", "production_critical", "database_migration", "security_sensitive"))
    )
    return "FAST_PATH" if eligible else "STANDARD"


def invocation_policy(state: dict[str, Any], agent: str, task_type: str | None = None) -> dict[str, Any]:
    """Aplica caps econômicos por papel sem permitir que o agent escolha o próprio modelo."""
    policy = load_reasoning_policy()
    requested = state["reasoning"]["current_level"]
    normalized_agent = agent.lower()
    normalized_task = (task_type or state["reasoning"]["signals"].get("task_type", "GENERAL")).upper()
    category = "router" if "router" in normalized_agent else "test" if "test" in normalized_agent or normalized_task == "TEST" else "documentation" if normalized_task in {"DOCUMENTATION", "EXPLANATION"} else "default"
    cap = policy["agent_caps"][category]
    order = {level: index for index, level in enumerate(REASONING_LEVELS)}
    effective_level = requested if order[requested] <= order[cap] else cap
    config = policy["levels"][effective_level]
    return {"level": effective_level, "model": config["model"], "reasoning_effort": config["reasoning_effort"], "context_budget": config["context_budget"], "max_input_tokens": config["max_input_tokens"], "cap": cap, "category": category}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def assert_safe_metadata(value: Any, key: str = "metadata") -> None:
    if SENSITIVE_KEY.search(key):
        raise RuntimeErrorSafe(f"campo sensível não permitido na telemetria: {key}")
    if isinstance(value, dict):
        for nested_key, nested in value.items():
            assert_safe_metadata(nested, str(nested_key))
    elif isinstance(value, list):
        for nested in value:
            assert_safe_metadata(nested, key)
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise RuntimeErrorSafe(f"valor potencialmente sensível recusado no campo {key}")


def config_hash() -> str:
    patterns = ("AGENTS.md", "config/AGENTS.md", "agents/*.toml", "contracts/*", "plugins/*/skills/*/SKILL.md", "plugins/*/skills/*/agents/openai.yaml")
    paths = sorted({path for pattern in patterns for path in ROOT.glob(pattern) if path.is_file()})
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def make_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(8)}"


def make_run_id() -> str:
    return f"jarvis-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(4)}"


def run_path(value: str | Path) -> Path:
    path = Path(value).resolve()
    if not (path / "state.json").is_file():
        raise RuntimeErrorSafe(f"execução inválida: state.json ausente em {path}")
    return path


def locked_run(function):
    """Serializa mutações de uma execução entre processos locais concorrentes."""
    @functools.wraps(function)
    def wrapper(args: argparse.Namespace):
        root = run_path(args.run_dir)
        lock_path = root / ".runtime.lock"
        with lock_path.open("a", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                return function(args)
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return wrapper


def telemetry_db_for_runs(runs_dir: Path) -> Path:
    resolved = runs_dir.resolve()
    return DEFAULT_TELEMETRY_DB if resolved == DEFAULT_RUNS_DIR.resolve() else resolved / ".telemetry/jarvis.db"


def telemetry_db_for_state(state: dict[str, Any], root: Path) -> Path:
    return Path(state.get("telemetry_db", root.parent / ".telemetry/jarvis.db")).resolve()


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY,task_id TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,duration_ms INTEGER NOT NULL,status TEXT NOT NULL,complexity TEXT NOT NULL,risk_class TEXT NOT NULL,operational_mode TEXT NOT NULL,reasoning_class TEXT NOT NULL,jarvis_version TEXT NOT NULL,policy_version TEXT NOT NULL,contracts_version TEXT NOT NULL,config_hash TEXT NOT NULL,budget_limit INTEGER NOT NULL,budget_used INTEGER NOT NULL,budget_override INTEGER NOT NULL,budget_override_reason TEXT,agent_invocation_count INTEGER NOT NULL,unique_agent_count INTEGER NOT NULL,rework_cycles INTEGER NOT NULL,stop_count INTEGER NOT NULL,first_pass_success INTEGER,human_gate_pass_on_first_attempt INTEGER,routing_outcome TEXT NOT NULL,input_tokens INTEGER NOT NULL,cached_input_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,credits REAL NOT NULL);
CREATE TABLE IF NOT EXISTS agent_invocations(invocation_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),agent TEXT NOT NULL,stage TEXT NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,finished_at TEXT,duration_ms INTEGER NOT NULL DEFAULT 0,model TEXT NOT NULL,reasoning_effort TEXT NOT NULL,input_tokens INTEGER NOT NULL DEFAULT 0,cached_input_tokens INTEGER NOT NULL DEFAULT 0,output_tokens INTEGER NOT NULL DEFAULT 0,credits REAL NOT NULL DEFAULT 0,agent_result TEXT,findings_count INTEGER NOT NULL DEFAULT 0,critical_findings_count INTEGER NOT NULL DEFAULT 0,parallel_batch TEXT,blocker TEXT,model_requested TEXT,model_effective TEXT,context_budget TEXT,progress_event TEXT,reasoning_effort_effective TEXT);
CREATE TABLE IF NOT EXISTS transitions(transition_id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL REFERENCES runs(run_id),source TEXT,target TEXT NOT NULL,at TEXT NOT NULL,reason TEXT NOT NULL,stop_reason TEXT,rework_origin TEXT,rework_reason TEXT);
CREATE TABLE IF NOT EXISTS handoffs(handoff_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),stage TEXT NOT NULL,created_at TEXT NOT NULL,output_path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings(finding_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),invocation_id TEXT NOT NULL REFERENCES agent_invocations(invocation_id),category TEXT NOT NULL,severity TEXT NOT NULL,actioned INTEGER NOT NULL,evidence_ref TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS human_gates(gate_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),attempt INTEGER NOT NULL,decision TEXT NOT NULL,reason_code TEXT NOT NULL,reason_detail TEXT,at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS decisions(decision_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),agent TEXT NOT NULL,category TEXT NOT NULL,decision TEXT NOT NULL,evidence_refs TEXT NOT NULL,confidence TEXT NOT NULL,confirmed_by TEXT,challenged_by TEXT,overridden_by TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS routing_snapshots(routing_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),agents_planned TEXT NOT NULL,agents_invoked TEXT NOT NULL,agents_skipped TEXT NOT NULL,agents_rejected_by_budget TEXT NOT NULL,parallel_batches INTEGER NOT NULL,routing_outcome TEXT NOT NULL,unnecessary_agents TEXT NOT NULL,missing_agents TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS release_evals(eval_id TEXT PRIMARY KEY,jarvis_version TEXT NOT NULL,config_hash TEXT NOT NULL,evaluated_at TEXT NOT NULL,routing_score REAL NOT NULL,over_routing_score REAL NOT NULL,under_routing_score REAL NOT NULL,sequence_score REAL NOT NULL,source_ref TEXT);
CREATE TABLE IF NOT EXISTS execution_attempts(execution_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),task_id TEXT NOT NULL,parent_execution_id TEXT,agent_type TEXT NOT NULL,task_type TEXT NOT NULL,policy_version TEXT NOT NULL,attempt_number INTEGER NOT NULL,initial_reasoning TEXT NOT NULL,effective_reasoning TEXT NOT NULL,complexity_score REAL NOT NULL,ambiguity_score REAL NOT NULL,escalated INTEGER NOT NULL,escalation_reason TEXT,input_tokens INTEGER NOT NULL DEFAULT 0,cached_input_tokens INTEGER NOT NULL DEFAULT 0,output_tokens INTEGER NOT NULL DEFAULT 0,total_tokens INTEGER NOT NULL DEFAULT 0,credits REAL NOT NULL DEFAULT 0,duration_ms INTEGER NOT NULL DEFAULT 0,files_read INTEGER NOT NULL DEFAULT 0,files_changed INTEGER NOT NULL DEFAULT 0,tool_calls INTEGER NOT NULL DEFAULT 0,tests_run INTEGER NOT NULL DEFAULT 0,tests_passed INTEGER NOT NULL DEFAULT 0,tests_failed INTEGER NOT NULL DEFAULT 0,review_findings INTEGER NOT NULL DEFAULT 0,success INTEGER,termination_reason TEXT,child_depth INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,finished_at TEXT,model_requested TEXT,model_effective TEXT,context_budget TEXT,progress_event TEXT,reasoning_effort_effective TEXT);
CREATE TABLE IF NOT EXISTS technical_handoffs(handoff_id TEXT PRIMARY KEY,task_id TEXT NOT NULL,run_id TEXT NOT NULL REFERENCES runs(run_id),execution_id TEXT,classification TEXT NOT NULL,summary TEXT NOT NULL,previous_behavior TEXT NOT NULL,new_behavior TEXT NOT NULL,reading_map_json TEXT NOT NULL,decisions_json TEXT NOT NULL,risks_json TEXT NOT NULL,test_evidence_json TEXT NOT NULL,output_path TEXT NOT NULL,created_at TEXT NOT NULL,policy_version TEXT NOT NULL,evidence_status TEXT NOT NULL,handoff_tokens INTEGER NOT NULL DEFAULT 0,handoff_duration_ms INTEGER NOT NULL DEFAULT 0,teachback_required INTEGER NOT NULL DEFAULT 0,teachback_questions INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS teachback_evaluations(evaluation_id TEXT PRIMARY KEY,handoff_id TEXT NOT NULL REFERENCES technical_handoffs(handoff_id),task_id TEXT NOT NULL,question_id TEXT NOT NULL,result TEXT NOT NULL,matched_concepts INTEGER NOT NULL,total_concepts INTEGER NOT NULL,duration_ms INTEGER NOT NULL DEFAULT 0,developer_requested_deeper_explanation INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
"""


def connect_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(DDL)
    for table in ("agent_invocations", "execution_attempts"):
        existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column in ("model_requested", "model_effective", "context_budget", "progress_event", "reasoning_effort_effective"):
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
    migrations = {
        "technical_handoffs": {"teachback_required": "INTEGER NOT NULL DEFAULT 0", "teachback_questions": "INTEGER NOT NULL DEFAULT 0"},
        "teachback_evaluations": {"developer_requested_deeper_explanation": "INTEGER NOT NULL DEFAULT 0"},
    }
    for table, columns in migrations.items():
        existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column, definition in columns.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return connection


def bool_int(value: bool | None) -> int | None:
    return None if value is None else int(value)


def sync_run(connection: sqlite3.Connection, state: dict[str, Any]) -> None:
    m, b, r = state["metrics"], state["budget"], state["routing"]
    values = (state["run_id"], state["task_id"], state["started_at"], state["finished_at"], m["duration_ms"], state["current_state"], state["complexity"], state["risk_class"], state["operational_mode"], state["reasoning_class"], state["jarvis_version"], state["policy_version"], state["contracts_version"], state["config_hash"], b["budget_limit"], b["budget_used"], int(b["budget_override"]), b["budget_override_reason"], m["agent_invocation_count"], len(state["agents_used"]), m["rework_cycles"], m["stop_count"], bool_int(m["first_pass_success"]), bool_int(m["human_gate_pass_on_first_attempt"]), r["routing_outcome"], m["input_tokens"], m["cached_input_tokens"], m["output_tokens"], m["credits"])
    connection.execute("""INSERT INTO runs(run_id,task_id,started_at,finished_at,duration_ms,status,complexity,risk_class,operational_mode,reasoning_class,jarvis_version,policy_version,contracts_version,config_hash,budget_limit,budget_used,budget_override,budget_override_reason,agent_invocation_count,unique_agent_count,rework_cycles,stop_count,first_pass_success,human_gate_pass_on_first_attempt,routing_outcome,input_tokens,cached_input_tokens,output_tokens,credits) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET finished_at=excluded.finished_at,duration_ms=excluded.duration_ms,status=excluded.status,reasoning_class=excluded.reasoning_class,budget_used=excluded.budget_used,budget_override=excluded.budget_override,budget_override_reason=excluded.budget_override_reason,agent_invocation_count=excluded.agent_invocation_count,unique_agent_count=excluded.unique_agent_count,rework_cycles=excluded.rework_cycles,stop_count=excluded.stop_count,first_pass_success=excluded.first_pass_success,human_gate_pass_on_first_attempt=excluded.human_gate_pass_on_first_attempt,routing_outcome=excluded.routing_outcome,input_tokens=excluded.input_tokens,cached_input_tokens=excluded.cached_input_tokens,output_tokens=excluded.output_tokens,credits=excluded.credits""", values)


def persist_state(root: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = now()
    state["metrics"]["duration_ms"] = elapsed_ms(state["started_at"], state["finished_at"] or state["updated_at"])
    write_json(root / "state.json", state)
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        sync_run(connection, state)


def initial_state(task_id: str, complexity: str, risk_class: str, operational_mode: str, decision: dict[str, Any], budget_justification: str | None, agents_planned: list[str] | None = None, telemetry_db: Path | None = None) -> dict[str, Any]:
    versions = load_json(VERSION_PATH)
    policy = load_reasoning_policy()
    timestamp = now()
    limit, parallel = BUDGETS[complexity]
    model_call_limit = min(policy["model_call_limits"][complexity], policy["budget"]["hard_max_model_calls"])
    context_limits = policy["context_limits"][decision["context_budget"]]
    cost_limits = policy["cost_limits"][complexity]
    return {
        "schema_version": versions["execution_state_schema_version"], "run_id": make_run_id(), "task_id": task_id,
        "jarvis_version": versions["jarvis_version"], "policy_version": decision["policy_version"],
        "registry_version": versions["policy_registry_version"],
        "contracts_version": versions["execution_state_schema_version"], "config_hash": config_hash(),
        "telemetry_db": str(telemetry_db or DEFAULT_TELEMETRY_DB), "created_at": timestamp,
        "started_at": timestamp, "updated_at": timestamp, "finished_at": None, "current_state": "NEW",
        "complexity": complexity, "risk_class": risk_class, "operational_mode": operational_mode,
        "execution_path": execution_path(complexity, risk_class, decision),
        "reasoning_class": decision["reasoning_class"],
        "reasoning": {
            "policy_version": decision["policy_version"],
            "signals": decision["signals"],
            "score": decision["score"],
            "contributions": decision["contributions"],
            "initial_level": decision["level"],
            "current_level": decision["level"],
            "final_level": None,
            "requested_effort": decision["reasoning_effort"],
            "effective_effort": None,
            "requested_model": decision["model"],
            "effective_model": None,
            "context_budget": decision["context_budget"],
            "max_input_tokens": decision["max_input_tokens"],
            "escalation_allowed": decision["escalation_allowed"],
            "escalations_used": 0,
            "max_escalations": decision["max_escalations"],
            "last_escalation_reason": None,
            "attempts_used": 0,
            "max_attempts": decision["max_attempts"],
            "max_child_depth": decision["max_child_depth"],
            "termination_reason": None
        },
        "budget": {"max_agents": limit, "max_parallel_agents": parallel, "required_reviewers": REQUIRED_REVIEWERS[risk_class], "budget_limit": limit, "budget_used": 0, "budget_override": bool(budget_justification), "budget_override_reason": "EXPLICIT_OVERRIDE" if budget_justification else None, "max_model_calls": model_call_limit, "hard_max_model_calls": policy["budget"]["hard_max_model_calls"], "model_calls_used": 0, "max_duration_ms": decision["max_duration_ms"], "progress_events": 0},
        "context_usage": {"mode": "OBSERVE_ONLY", "files": 0, "estimated_tokens": 0, "tool_reads": 0, "raw_bytes": 0, "limit_hits": 0, "limits": context_limits.copy()},
        "cost_budget": {"mode": policy["cost_limits"]["mode"], "soft_limit_ratio": policy["cost_limits"]["soft_limit_ratio"], "max_credits": cost_limits["max_credits"], "max_uncached_input_tokens": cost_limits["max_uncached_input_tokens"], "status": "ALLOW", "limit_hits": 0},
        "history": [{"from": None, "to": "NEW", "at": timestamp, "reason": "run initialized", "stop_reason": None}],
        "agents_used": [],
        "routing": {"agents_planned": sorted(set(agents_planned or [])), "agents_invoked": [], "agents_skipped": [], "agents_rejected_by_budget": [], "parallel_batches": 0, "routing_outcome": "UNKNOWN", "unnecessary_agents": [], "missing_agents": []},
        "metrics": {"duration_ms": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "credits": 0.0, "retry_count": 0, "agent_invocation_count": 0, "rework_cycles": 0, "stop_count": 0, "stop_reasons": {}, "handoff_count": 0, "first_pass_success": None, "human_gate_pass_on_first_attempt": None},
        "gate_decision": None, "gate_reason_code": None, "gate_reason_detail": None, "gate_attempts": 0,
    }


def observe_usage(state: dict[str, Any], values: dict[str, int | float]) -> list[str]:
    """Atualiza métricas observadas sem alegar bloqueio preventivo do executor."""
    usage = state["context_usage"]
    usage["files"] += int(values["files_read"])
    usage["estimated_tokens"] += int(values["input_tokens"])
    usage["tool_reads"] += int(values["tool_calls"])
    checks = {"files": "max_files", "estimated_tokens": "max_context_tokens", "tool_reads": "max_tool_reads", "raw_bytes": "max_raw_bytes"}
    warnings = [f"CONTEXT_LIMIT_OBSERVED:{key}" for key, limit_key in checks.items() if usage[key] > usage["limits"][limit_key]]
    if warnings:
        usage["limit_hits"] += len(warnings)
    cost = state["cost_budget"]
    projected_credits = state["metrics"]["credits"] + float(values["credits"])
    projected_uncached = state["metrics"]["input_tokens"] + int(values["input_tokens"]) - state["metrics"]["cached_input_tokens"] - int(values["cached_input_tokens"])
    hard = projected_credits >= cost["max_credits"] or projected_uncached >= cost["max_uncached_input_tokens"]
    soft = projected_credits >= cost["max_credits"] * cost["soft_limit_ratio"] or projected_uncached >= cost["max_uncached_input_tokens"] * cost["soft_limit_ratio"]
    cost["status"] = "HARD_LIMIT_OBSERVED" if hard else "SOFT_LIMIT_OBSERVED" if soft else "ALLOW"
    if cost["status"] != "ALLOW":
        cost["limit_hits"] += 1
        warnings.append(f"COST_{cost['status']}")
    return warnings


def initialize(args: argparse.Namespace) -> dict[str, Any]:
    assert_safe_metadata({"task_id": args.task_id, "agents_planned": getattr(args, "agents_planned", [])})
    signals = task_signals_from_args(args)
    decision = reasoning_decision(signals)
    manual_class = getattr(args, "reasoning_class", None)
    if manual_class:
        raise RuntimeErrorSafe("--reasoning-class não pode sobrescrever a policy V3")
    if args.risk_class == "CRITICAL" or args.complexity == "CRITICAL":
        config = load_reasoning_policy()["levels"]["HIGH"]
        decision.update({"level": "HIGH", "reasoning_class": config["reasoning_class"], "reasoning_effort": config["reasoning_effort"], "model": config["model"], "context_budget": config["context_budget"], "max_input_tokens": config["max_input_tokens"], "escalation_allowed": False, "reason": "CRITICAL floor: HIGH"})
    if args.complexity in {"TRANSVERSAL", "CRITICAL"} and decision["reasoning_class"] == "FAST":
        raise RuntimeErrorSafe("TRANSVERSAL/CRITICAL não pode iniciar em INSTANT; informe sinais suficientes para MEDIUM ou HIGH")
    runs_dir = Path(args.runs_dir).resolve()
    db_path = Path(getattr(args, "telemetry_db", None) or telemetry_db_for_runs(runs_dir)).resolve()
    state = initial_state(args.task_id, args.complexity, args.risk_class, args.operational_mode, decision, args.budget_justification, getattr(args, "agents_planned", []), db_path)
    root = runs_dir / state["run_id"]
    root.mkdir(parents=True, exist_ok=False)
    (root / "context-packs").mkdir()
    persist_state(root, state)
    append_jsonl(root / "events.jsonl", {"event": "RUN_INITIALIZED", "at": state["created_at"], "run_id": state["run_id"], "state": "NEW"})
    with connect_db(db_path) as connection:
        connection.execute("INSERT INTO transitions(run_id,source,target,at,reason) VALUES(?,?,?,?,?)", (state["run_id"], None, "NEW", state["created_at"], "run initialized"))
    return {"run_dir": str(root), "telemetry_db": str(db_path), "state": state}


def transition(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    source, target = state["current_state"], args.to
    if target not in TRANSITIONS.get(source, set()):
        raise RuntimeErrorSafe(f"transição não permitida: {source} -> {target}")
    if source == "NEW" and target == "PLAN_APPROVED" and state["complexity"] not in {"TRIVIAL", "LOCALIZED"}:
        raise RuntimeErrorSafe("somente tarefas TRIVIAL/LOCALIZED podem usar aprovação implícita do pedido direto")
    if state["operational_mode"] == "READ_ONLY_AUDIT" and target == "IMPLEMENTING":
        raise RuntimeErrorSafe("READ_ONLY_AUDIT não permite transição para IMPLEMENTING")
    stop_reason, gate = getattr(args, "stop_reason", None), getattr(args, "gate_decision", None)
    gate_code, gate_detail = getattr(args, "gate_reason_code", None), getattr(args, "gate_reason_detail", None)
    origin, rework_reason = getattr(args, "rework_origin", None), getattr(args, "rework_reason", None)
    if (target == "BLOCKED") != bool(stop_reason):
        raise RuntimeErrorSafe("transição para BLOCKED exige --stop-reason, exclusivo desse destino")
    rework = target == "IMPLEMENTING" and source in {"VALIDATING", "REVIEW_READY", "HUMAN_GATE", "HOMOLOGATION_READY"}
    if rework and (not origin or not rework_reason):
        raise RuntimeErrorSafe("retorno à implementação exige --rework-origin e --rework-reason")
    if gate:
        if source != "HUMAN_GATE":
            raise RuntimeErrorSafe("--gate-decision só pode ser registrado a partir de HUMAN_GATE")
        gate_code = gate_code or ("APPROVED_AS_PLANNED" if gate == "APPROVED" else None)
        if not gate_code:
            raise RuntimeErrorSafe("gate CHANGES_REQUESTED/REJECTED exige --gate-reason-code")
        if gate == "APPROVED" and gate_code != "APPROVED_AS_PLANNED":
            raise RuntimeErrorSafe("gate APPROVED usa APPROVED_AS_PLANNED")
    if source == "HUMAN_GATE" and target != "BLOCKED" and not gate:
        raise RuntimeErrorSafe("saída do HUMAN_GATE exige --gate-decision")
    if source == "HUMAN_GATE" and target in {"DONE", "HOMOLOGATION_READY"} and gate != "APPROVED":
        raise RuntimeErrorSafe("somente gate APPROVED pode avançar para conclusão ou homologação")
    if source == "HUMAN_GATE" and target == "IMPLEMENTING" and gate not in {"CHANGES_REQUESTED", "REJECTED"}:
        raise RuntimeErrorSafe("retorno do gate à implementação exige CHANGES_REQUESTED ou REJECTED")
    timestamp = now()
    entry = {"from": source, "to": target, "at": timestamp, "reason": args.reason, "stop_reason": stop_reason, "rework_origin": origin, "rework_reason": rework_reason}
    state["current_state"] = target
    state["history"].append(entry)
    if target == "HUMAN_GATE" and state["metrics"]["first_pass_success"] is None:
        state["metrics"]["first_pass_success"] = state["metrics"]["rework_cycles"] == 0
    if rework:
        state["metrics"]["rework_cycles"] += 1
    if target == "BLOCKED":
        state["metrics"]["stop_count"] += 1
        reasons = state["metrics"]["stop_reasons"]
        reasons[stop_reason] = reasons.get(stop_reason, 0) + 1
    if target == "DONE":
        state["finished_at"] = timestamp
        if "reasoning" in state:
            state["reasoning"]["final_level"] = state["reasoning"]["current_level"]
            state["reasoning"]["termination_reason"] = state["reasoning"]["termination_reason"] or "SUCCESS"
    assert_safe_metadata({"reason": args.reason, "gate_reason_detail": gate_detail or ""})
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        connection.execute("INSERT INTO transitions(run_id,source,target,at,reason,stop_reason,rework_origin,rework_reason) VALUES(?,?,?,?,?,?,?,?)", (state["run_id"], source, target, timestamp, args.reason, stop_reason, origin, rework_reason))
        if gate:
            state["gate_attempts"] += 1
            state["gate_decision"], state["gate_reason_code"], state["gate_reason_detail"] = gate, gate_code, gate_detail
            if gate == "APPROVED":
                state["metrics"]["human_gate_pass_on_first_attempt"] = state["gate_attempts"] == 1
            connection.execute("INSERT INTO human_gates VALUES(?,?,?,?,?,?,?)", (make_id("gate"), state["run_id"], state["gate_attempts"], gate, gate_code, gate_detail, timestamp))
    append_jsonl(root / "events.jsonl", {"event": "STATE_TRANSITION", "run_id": state["run_id"], **entry})
    persist_state(root, state)
    return state


def _nonnegative(values: dict[str, int | float]) -> None:
    for key, value in values.items():
        if value < 0:
            raise RuntimeErrorSafe(f"{key} não pode ser negativo")


def _register_agent(state: dict[str, Any], agent: str, justification: str | None) -> None:
    if agent in state["agents_used"]:
        return
    projected = len(state["agents_used"]) + 1
    if projected > state["budget"]["budget_limit"] and not justification:
        rejected = state["routing"]["agents_rejected_by_budget"]
        if agent not in rejected:
            rejected.append(agent)
            rejected.sort()
        raise RuntimeErrorSafe(f"budget excedido: {projected} agentes para máximo {state['budget']['budget_limit']}; informe --budget-justification")
    state["agents_used"].append(agent)
    state["agents_used"].sort()
    state["routing"]["agents_invoked"] = list(state["agents_used"])
    state["budget"]["budget_used"] = len(state["agents_used"])
    if projected > state["budget"]["budget_limit"]:
        state["budget"]["budget_override"] = True
        state["budget"]["budget_override_reason"] = "EXPLICIT_OVERRIDE"


@locked_run
def invocation_start(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    reasoning = state.get("reasoning", {})
    call_policy = invocation_policy(state, args.agent, getattr(args, "task_type", None))
    required_model = call_policy["model"]
    model = getattr(args, "model", None) or required_model
    assert_safe_metadata({"agent": args.agent, "model": model, "parallel_batch": getattr(args, "parallel_batch", None), "parent_execution_id": getattr(args, "parent_execution_id", None) or ""})
    if model != required_model:
        raise RuntimeErrorSafe(f"modelo divergente da policy: esperado {required_model}, recebido {model}")
    budget = state["budget"]
    if budget.get("model_calls_used", 0) >= budget.get("max_model_calls", 1):
        reasoning["termination_reason"] = "BUDGET_EXHAUSTED"
        persist_state(root, state)
        raise RuntimeErrorSafe(f"budget de chamadas de modelo excedido: {budget.get('model_calls_used', 0)}/{budget.get('max_model_calls', 1)}")
    if elapsed_ms(state["started_at"], now()) >= budget.get("max_duration_ms", 1):
        reasoning["termination_reason"] = "BUDGET_EXHAUSTED"
        persist_state(root, state)
        raise RuntimeErrorSafe("budget de duração da tarefa excedido")
    try:
        _register_agent(state, args.agent, getattr(args, "budget_justification", None))
    except RuntimeErrorSafe:
        persist_state(root, state)
        append_jsonl(root / "events.jsonl", {"event": "AGENT_REJECTED_BY_BUDGET", "at": now(), "run_id": state["run_id"], "agent": args.agent})
        raise
    invocation_id, started_at = getattr(args, "invocation_id", None) or make_id("inv"), now()
    batch = getattr(args, "parallel_batch", None)
    max_attempts = reasoning.get("max_attempts", 3)
    parent_execution_id = getattr(args, "parent_execution_id", None)
    attempt_number = getattr(args, "attempt_number", None)
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        running_calls = connection.execute("SELECT COUNT(*) FROM agent_invocations WHERE run_id=? AND finished_at IS NULL", (state["run_id"],)).fetchone()[0]
        if running_calls >= budget["max_parallel_agents"]:
            raise RuntimeErrorSafe(f"budget de paralelismo excedido: {running_calls}/{budget['max_parallel_agents']}")
        parent = None
        if parent_execution_id:
            parent = connection.execute(
                "SELECT execution_id,child_depth FROM execution_attempts WHERE execution_id=? AND run_id=?",
                (parent_execution_id, state["run_id"]),
            ).fetchone()
            if not parent:
                raise RuntimeErrorSafe("parent_execution_id inexistente nesta execução")
        expected_depth = parent["child_depth"] + 1 if parent else 0
        if (getattr(args, "child_depth", 0) or 0) != expected_depth:
            raise RuntimeErrorSafe(f"child_depth inconsistente com parent: esperado {expected_depth}")
        child_executions = connection.execute(
            "SELECT COUNT(*) FROM execution_attempts WHERE run_id=? AND parent_execution_id IS NOT NULL AND attempt_number=1",
            (state["run_id"],),
        ).fetchone()[0]
        child_calls = connection.execute("SELECT COUNT(*) FROM execution_attempts WHERE run_id=? AND parent_execution_id IS NOT NULL", (state["run_id"],)).fetchone()[0]
        next_chain_attempt = connection.execute(
            "SELECT COALESCE(MAX(attempt_number),0)+1 FROM execution_attempts WHERE run_id=? AND agent_type=? AND COALESCE(parent_execution_id,'')=COALESCE(?,'')",
            (state["run_id"], args.agent, parent_execution_id),
        ).fetchone()[0]
        retries_used = connection.execute(
            "SELECT COUNT(*)-COUNT(DISTINCT agent_type || ':' || COALESCE(parent_execution_id,'')) FROM execution_attempts WHERE run_id=?",
            (state["run_id"],),
        ).fetchone()[0]
    if attempt_number is None:
        attempt_number = next_chain_attempt
    elif attempt_number != next_chain_attempt:
        raise RuntimeErrorSafe(f"attempt_number deve seguir o contador da cadeia: esperado {next_chain_attempt}")
    max_total_retries = load_reasoning_policy()["budget"].get("max_total_retries", max_attempts)
    max_child_executions = load_reasoning_policy()["budget"].get("max_child_executions", max_attempts)
    if parent_execution_id and next_chain_attempt == 1 and child_executions >= max_child_executions:
        raise RuntimeErrorSafe(f"budget global de child executions excedido: {child_executions}/{max_child_executions}")
    child_call_limit = max(1, budget["max_model_calls"] // 2)
    if parent_execution_id and child_calls >= child_call_limit:
        raise RuntimeErrorSafe(f"fração do budget de chamadas para children excedida: {child_calls}/{child_call_limit}")
    if attempt_number > 1 and retries_used >= max_total_retries:
        raise RuntimeErrorSafe(f"budget global de retries excedido: {retries_used}/{max_total_retries}")
    if attempt_number < 1 or attempt_number > max_attempts:
        if reasoning:
            reasoning["termination_reason"] = "BUDGET_EXHAUSTED"
            persist_state(root, state)
        raise RuntimeErrorSafe(f"budget de tentativas excedido: {attempt_number}/{max_attempts}")
    progress_event = getattr(args, "progress_event", None)
    if attempt_number > 1 and progress_event not in PROGRESS_EVENTS:
        raise RuntimeErrorSafe("retry exige --progress-event verificável para evitar consumo sem progresso")
    child_depth = getattr(args, "child_depth", 0) or 0
    if child_depth < 0 or child_depth > reasoning.get("max_child_depth", 3):
        raise RuntimeErrorSafe(f"profundidade de child agent excedida: {child_depth}")
    legacy_level = {"FAST": "INSTANT", "NORMAL": "MEDIUM", "DEEP": "HIGH"}.get(state.get("reasoning_class"), "MEDIUM")
    legacy_effort = {"INSTANT": "low", "MEDIUM": "medium", "HIGH": "high"}[legacy_level]
    required_effort = call_policy.get("reasoning_effort") or legacy_effort
    effort = getattr(args, "reasoning_effort", None) or required_effort
    if effort not in REASONING_EFFORTS:
        raise RuntimeErrorSafe(f"reasoning_effort inválido: {effort}")
    if effort != required_effort:
        raise RuntimeErrorSafe(f"reasoning_effort divergente da policy: esperado {required_effort}, recebido {effort}")
    if reasoning:
        reasoning["attempts_used"] = max(reasoning["attempts_used"], attempt_number)
    budget["model_calls_used"] = budget.get("model_calls_used", 0) + 1
    if progress_event:
        budget["progress_events"] = budget.get("progress_events", 0) + 1
    state["metrics"]["agent_invocation_count"] += 1
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        if batch and connection.execute("SELECT COUNT(*) FROM agent_invocations WHERE run_id=? AND parallel_batch=?", (state["run_id"], batch)).fetchone()[0] == 0:
            state["routing"]["parallel_batches"] += 1
        connection.execute("INSERT INTO agent_invocations(invocation_id,run_id,agent,stage,status,started_at,model,reasoning_effort,parallel_batch,model_requested,model_effective,context_budget,progress_event) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (invocation_id, state["run_id"], args.agent, args.stage, "RUNNING", started_at, model, effort, batch, required_model, None, call_policy["context_budget"], progress_event))
        signals = reasoning.get("signals", {})
        connection.execute("""INSERT INTO execution_attempts(execution_id,run_id,task_id,parent_execution_id,agent_type,task_type,policy_version,attempt_number,initial_reasoning,effective_reasoning,complexity_score,ambiguity_score,escalated,escalation_reason,child_depth,created_at,model_requested,model_effective,context_budget,progress_event) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            invocation_id, state["run_id"], state["task_id"], parent_execution_id, args.agent,
            getattr(args, "task_type", None) or signals.get("task_type", "GENERAL"), reasoning.get("policy_version", state["policy_version"]),
            attempt_number, reasoning.get("initial_level", legacy_level), call_policy["level"],
            signals.get("complexity_score", 0), signals.get("ambiguity_score", 0), int(reasoning.get("escalations_used", 0) > 0),
            reasoning.get("last_escalation_reason"), child_depth, started_at, required_model, None, call_policy["context_budget"], progress_event,
        ))
    event = {"event": "AGENT_INVOCATION_STARTED", "at": started_at, "run_id": state["run_id"], "invocation_id": invocation_id, "agent": args.agent, "stage": args.stage, "status": "RUNNING", "model_requested": required_model, "model_effective": None, "reasoning_effort": effort, "reasoning_level": call_policy["level"], "context_budget": call_policy["context_budget"], "max_input_tokens": call_policy["max_input_tokens"], "agent_cap": call_policy["cap"], "attempt_number": attempt_number, "progress_event": progress_event, "parallel_batch": batch}
    append_jsonl(root / "events.jsonl", event)
    persist_state(root, state)
    return event


@locked_run
def invocation_finish(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    values = {key: getattr(args, key, 0) or 0 for key in ("input_tokens", "cached_input_tokens", "output_tokens", "credits", "retry_count", "files_read", "files_changed", "tool_calls", "tests_run", "tests_passed", "tests_failed", "review_findings")}
    _nonnegative(values)
    if values["cached_input_tokens"] > values["input_tokens"]:
        raise RuntimeErrorSafe("cached_input_tokens não pode exceder input_tokens")
    finished_at = now()
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        row = connection.execute("SELECT * FROM agent_invocations WHERE invocation_id=? AND run_id=?", (args.invocation_id, state["run_id"])).fetchone()
        if not row:
            raise RuntimeErrorSafe(f"invocação desconhecida nesta execução: {args.invocation_id}")
        if row["finished_at"]:
            raise RuntimeErrorSafe(f"invocação já finalizada: {args.invocation_id}")
        duration = elapsed_ms(row["started_at"], finished_at)
        observed_model = getattr(args, "model_effective", None)
        observed_effort = getattr(args, "reasoning_effort_effective", None)
        connection.execute("UPDATE agent_invocations SET status=?,finished_at=?,duration_ms=?,input_tokens=?,cached_input_tokens=?,output_tokens=?,credits=?,agent_result=?,blocker=NULL,model_effective=?,reasoning_effort_effective=? WHERE invocation_id=?", (args.status, finished_at, duration, values["input_tokens"], values["cached_input_tokens"], values["output_tokens"], values["credits"], args.agent_result, observed_model, observed_effort, args.invocation_id))
        success_arg = getattr(args, "success", None)
        success = args.status == "OK" if success_arg is None else bool(success_arg)
        termination = getattr(args, "termination_reason", None) or ("SUCCESS" if success else "TOOL_FAILURE")
        if termination not in TERMINATION_REASONS:
            raise RuntimeErrorSafe(f"termination_reason inválido: {termination}")
        if termination == "TEST_FAILURE" and not (values["tests_run"] > 0 and values["tests_failed"] > 0):
            raise RuntimeErrorSafe("TEST_FAILURE exige tests_run > 0 e tests_failed > 0")
        context_limit = next(config["max_input_tokens"] for config in load_reasoning_policy()["levels"].values() if config["context_budget"] == row["context_budget"])
        if values["input_tokens"] > context_limit or elapsed_ms(state["started_at"], finished_at) > state["budget"]["max_duration_ms"]:
            success, termination = False, "BUDGET_EXHAUSTED"
            state["reasoning"]["termination_reason"] = termination
        connection.execute("""UPDATE execution_attempts SET input_tokens=?,cached_input_tokens=?,output_tokens=?,total_tokens=?,credits=?,duration_ms=?,files_read=?,files_changed=?,tool_calls=?,tests_run=?,tests_passed=?,tests_failed=?,review_findings=?,success=?,termination_reason=?,finished_at=?,model_effective=?,reasoning_effort_effective=? WHERE execution_id=?""", (
            values["input_tokens"], values["cached_input_tokens"], values["output_tokens"], values["input_tokens"] + values["output_tokens"],
            values["credits"], duration, values["files_read"], values["files_changed"], values["tool_calls"], values["tests_run"],
            values["tests_passed"], values["tests_failed"], values["review_findings"], int(success), termination, finished_at, observed_model, observed_effort, args.invocation_id,
        ))
    if observed_model is not None:
        state["reasoning"]["effective_model"] = observed_model
    if observed_effort is not None:
        state["reasoning"]["effective_effort"] = observed_effort
    budget_warnings = observe_usage(state, values)
    for key in ("input_tokens", "cached_input_tokens", "output_tokens", "credits", "retry_count"):
        state["metrics"][key] += values[key]
    event = {"event": "AGENT_INVOCATION_FINISHED", "at": finished_at, "run_id": state["run_id"], "invocation_id": args.invocation_id, "agent": row["agent"], "stage": row["stage"], "status": args.status, "duration_ms": duration, "model_requested": row["model_requested"], "model_effective": observed_model, "reasoning_effort_requested": row["reasoning_effort"], "reasoning_effort_effective": observed_effort, "context_budget": row["context_budget"], "agent_result": args.agent_result, "success": success, "termination_reason": termination, "budget_warnings": budget_warnings, **{key: values[key] for key in ("input_tokens", "cached_input_tokens", "output_tokens", "credits", "files_changed", "tests_passed", "tests_failed", "tool_calls")}}
    assert_safe_metadata(event)
    append_jsonl(root / "events.jsonl", event)
    persist_state(root, state)
    return event


@locked_run
def evaluate_attempt(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    reasoning = state.get("reasoning")
    if not reasoning:
        raise RuntimeErrorSafe("execução anterior à V3 não possui estado de adaptive reasoning")
    policy = load_reasoning_policy()
    reason = getattr(args, "escalation_reason", None)
    success = bool(getattr(args, "success", False))
    if success and reason:
        raise RuntimeErrorSafe("resultado de sucesso não aceita escalation_reason")
    if success:
        reasoning["final_level"] = reasoning["current_level"]
        reasoning["termination_reason"] = "SUCCESS"
        outcome = {"escalate": False, "reasoning_level": reasoning["current_level"], "reasoning_effort": reasoning["requested_effort"], "model": reasoning["requested_model"], "context_budget": reasoning["context_budget"], "termination_reason": "SUCCESS"}
    else:
        if reason not in policy["escalation"]["triggers"]:
            raise RuntimeErrorSafe("falha exige escalation_reason configurado na policy")
        previous_id = getattr(args, "previous_execution_id", None)
        if not previous_id:
            raise RuntimeErrorSafe("falha exige previous_execution_id verificável")
        with connect_db(telemetry_db_for_state(state, root)) as connection:
            previous = connection.execute(
                "SELECT * FROM execution_attempts WHERE execution_id=? AND run_id=? AND finished_at IS NOT NULL AND success=0",
                (previous_id, state["run_id"]),
            ).fetchone()
        if not previous:
            raise RuntimeErrorSafe("tentativa anterior inexistente, não finalizada ou sem falha")
        trigger_valid = {
            "TEST_FAILURE": previous["tests_run"] > 0 and previous["tests_failed"] > 0,
            "REPEATED_TOOL_FAILURE": previous["termination_reason"] == "TOOL_FAILURE",
            "CRITICAL_REVIEW_FINDING": previous["review_findings"] > 0,
            "RESULT_INCONSISTENCY": previous["termination_reason"] in {"TEST_FAILURE", "TOOL_FAILURE", "HUMAN_REVIEW_REQUIRED"},
            "UNPLANNED_ARCHITECTURE": previous["termination_reason"] == "HUMAN_REVIEW_REQUIRED",
            "SCOPE_EXPANDED": previous["termination_reason"] == "HUMAN_REVIEW_REQUIRED",
        }[reason]
        if not trigger_valid:
            raise RuntimeErrorSafe(f"gatilho {reason} não é comprovado pela tentativa anterior")
        allowed = (
            policy["escalation"]["enabled"]
            and reasoning["escalation_allowed"]
            and reasoning["current_level"] == policy["escalation"]["allowed_from"]
            and reasoning["escalations_used"] < reasoning["max_escalations"]
            and reasoning["attempts_used"] < reasoning["max_attempts"]
        )
        if allowed:
            target = policy["escalation"]["target"]
            target_config = policy["levels"][target]
            reasoning["current_level"] = target
            reasoning["requested_effort"] = target_config["reasoning_effort"]
            reasoning["requested_model"] = target_config["model"]
            reasoning["context_budget"] = target_config["context_budget"]
            reasoning["max_input_tokens"] = target_config["max_input_tokens"]
            reasoning["escalations_used"] += 1
            reasoning["last_escalation_reason"] = reason
            reasoning["escalation_allowed"] = False
            state["reasoning_class"] = target_config["reasoning_class"]
            context = {
                "schema_version": load_json(VERSION_PATH)["execution_state_schema_version"],
                "run_id": state["run_id"],
                "previous_execution_id": getattr(args, "previous_execution_id", None),
                "changed_files": sorted(set(getattr(args, "changed_files", None) or [])),
                "tests_failed": getattr(args, "tests_failed", 0) or 0,
                "failed_hypotheses_count": getattr(args, "failed_hypotheses_count", 0) or 0,
                "escalation_reason": reason,
                "target_reasoning": target,
                "target_model": target_config["model"],
                "context_budget": target_config["context_budget"],
            }
            assert_safe_metadata(context)
            write_json(root / "escalation-context.json", context)
            outcome = {"escalate": True, "reasoning_level": target, "reasoning_effort": target_config["reasoning_effort"], "model": target_config["model"], "context_budget": target_config["context_budget"], "termination_reason": None, "context": str(root / "escalation-context.json")}
        else:
            termination = "BUDGET_EXHAUSTED" if reasoning["attempts_used"] >= reasoning["max_attempts"] or reasoning["escalations_used"] >= reasoning["max_escalations"] else "HUMAN_REVIEW_REQUIRED"
            reasoning["final_level"] = reasoning["current_level"]
            reasoning["termination_reason"] = termination
            outcome = {"escalate": False, "reasoning_level": reasoning["current_level"], "reasoning_effort": reasoning["requested_effort"], "model": reasoning["requested_model"], "context_budget": reasoning["context_budget"], "termination_reason": termination}
    event = {"event": "EXECUTION_EVALUATED", "at": now(), "run_id": state["run_id"], "escalation_reason": reason, **outcome}
    assert_safe_metadata(event)
    append_jsonl(root / "events.jsonl", event)
    persist_state(root, state)
    return outcome


def record(args: argparse.Namespace) -> dict[str, Any]:
    """Compatibilidade V2: registra uma invocação completa em uma chamada."""
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    if state.get("schema_version") == load_json(VERSION_PATH)["execution_state_schema_version"]:
        raise RuntimeErrorSafe("record legado não é permitido em runs V3; use invocation-start/invocation-finish")
    started, finished = getattr(args, "started_at", None) or now(), getattr(args, "finished_at", None) or now()
    credits_arg = getattr(args, "credits", None)
    values = {"duration_ms": getattr(args, "duration_ms", None) or elapsed_ms(started, finished), "input_tokens": getattr(args, "input_tokens", 0) or 0, "cached_input_tokens": getattr(args, "cached_input_tokens", 0) or 0, "output_tokens": getattr(args, "output_tokens", 0) or 0, "credits": getattr(args, "token_or_credit_cost", 0) or 0 if credits_arg is None else credits_arg, "retry_count": getattr(args, "retry_count", 0) or 0}
    _nonnegative(values)
    if values["cached_input_tokens"] > values["input_tokens"]:
        raise RuntimeErrorSafe("cached_input_tokens não pode exceder input_tokens")
    agent = getattr(args, "agent", None)
    if agent:
        try:
            _register_agent(state, agent, getattr(args, "budget_justification", None))
        except RuntimeErrorSafe:
            persist_state(root, state)
            raise
        invocation_id = make_id("inv")
        state["metrics"]["agent_invocation_count"] += 1
        model = getattr(args, "model", None) or "unknown"
        effort = getattr(args, "reasoning_effort", None) or str(getattr(args, "reasoning_class", "NORMAL")).lower()
        with connect_db(telemetry_db_for_state(state, root)) as connection:
            connection.execute("INSERT INTO agent_invocations(invocation_id,run_id,agent,stage,status,started_at,finished_at,duration_ms,model,reasoning_effort,input_tokens,cached_input_tokens,output_tokens,credits,agent_result,findings_count,critical_findings_count,parallel_batch,blocker,model_requested,model_effective) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (invocation_id, state["run_id"], agent, args.stage, args.status, started, finished, values["duration_ms"], model, effort, values["input_tokens"], values["cached_input_tokens"], values["output_tokens"], values["credits"], getattr(args, "agent_result", None), getattr(args, "findings_count", 0) or 0, getattr(args, "critical_findings_count", 0) or 0, getattr(args, "parallel_batch", None), None, model, model))
    for key in ("input_tokens", "cached_input_tokens", "output_tokens", "credits", "retry_count"):
        state["metrics"][key] += values[key]
    event = {"event": "STAGE_RECORDED", "at": now(), "run_id": state["run_id"], "invocation_id": invocation_id if agent else None, "agent": agent, "stage": args.stage, "status": args.status, "started_at": started, "finished_at": finished, **values}
    assert_safe_metadata(event)
    append_jsonl(root / "events.jsonl", event)
    persist_state(root, state)
    return event


def finding(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    finding_id, created_at = getattr(args, "finding_id", None) or make_id("finding"), now()
    evidence_ref = getattr(args, "evidence_ref", None)
    assert_safe_metadata({"category": args.category, "evidence_ref": evidence_ref or ""})
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        if not connection.execute("SELECT 1 FROM agent_invocations WHERE invocation_id=? AND run_id=?", (args.invocation_id, state["run_id"])).fetchone():
            raise RuntimeErrorSafe(f"invocação desconhecida nesta execução: {args.invocation_id}")
        connection.execute("INSERT INTO findings VALUES(?,?,?,?,?,?,?,?)", (finding_id, state["run_id"], args.invocation_id, args.category, args.severity, int(args.actioned), evidence_ref, created_at))
        counts = connection.execute("SELECT COUNT(*) total,SUM(severity='CRITICAL') critical FROM findings WHERE invocation_id=?", (args.invocation_id,)).fetchone()
        connection.execute("UPDATE agent_invocations SET findings_count=?,critical_findings_count=? WHERE invocation_id=?", (counts["total"], counts["critical"] or 0, args.invocation_id))
    event = {"event": "FINDING_RECORDED", "at": created_at, "run_id": state["run_id"], "finding_id": finding_id, "invocation_id": args.invocation_id, "category": args.category, "severity": args.severity, "finding_actioned": bool(args.actioned), "evidence_ref": evidence_ref}
    append_jsonl(root / "events.jsonl", event)
    return event


def route(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    for field in ("agents_planned", "agents_skipped", "agents_rejected_by_budget", "unnecessary_agents", "missing_agents"):
        value = getattr(args, field, None)
        if value is not None:
            state["routing"][field] = sorted(set(value))
    state["routing"]["agents_invoked"] = list(state["agents_used"])
    state["routing"]["routing_outcome"] = args.routing_outcome
    assert_safe_metadata(state["routing"])
    event = {"event": "ROUTING_EVALUATED", "at": now(), "run_id": state["run_id"], **state["routing"]}
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        routing = state["routing"]
        connection.execute(
            "INSERT INTO routing_snapshots VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (make_id("routing"), state["run_id"], json.dumps(routing["agents_planned"]),
             json.dumps(routing["agents_invoked"]), json.dumps(routing["agents_skipped"]),
             json.dumps(routing["agents_rejected_by_budget"]), routing["parallel_batches"],
             routing["routing_outcome"], json.dumps(routing["unnecessary_agents"]),
             json.dumps(routing["missing_agents"]), event["at"]),
        )
    append_jsonl(root / "events.jsonl", event)
    persist_state(root, state)
    return event


def decision(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    decision_id, created_at = getattr(args, "decision_id", None) or make_id("decision"), now()
    refs = sorted(set(args.evidence_ref))
    payload = {"decision_id": decision_id, "agent": args.agent, "category": args.category, "decision": args.decision, "evidence_refs": refs, "confidence": args.confidence, "confirmed_by": getattr(args, "confirmed_by", None), "challenged_by": getattr(args, "challenged_by", None), "overridden_by": getattr(args, "overridden_by", None)}
    assert_safe_metadata(payload)
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        connection.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?,?)", (decision_id, state["run_id"], args.agent, args.category, args.decision, json.dumps(refs, ensure_ascii=False), args.confidence, payload["confirmed_by"], payload["challenged_by"], payload["overridden_by"], created_at))
    event = {"event": "DECISION_RECORDED", "at": created_at, "run_id": state["run_id"], **payload}
    append_jsonl(root / "events.jsonl", event)
    return event


def handoff_template(state: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "2.0.0", "run_id": state["run_id"], "jarvis_version": state["jarvis_version"], "status": "IN_PROGRESS", "stage": state["current_state"], "complexity": state["complexity"], "risk_class": state["risk_class"], "operational_mode": state["operational_mode"], "reasoning_class": state["reasoning_class"], "requirement_ids": [], "files": [], "contracts_changed": [], "decisions": [], "validations": {"executed": [], "passed": [], "failed": [], "not_executed": []}, "risks": [], "limitations": [], "blockers": [], "stop_reason": None, "ownership": {}, "next": []}


def create_handoff(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    destination = Path(args.output).resolve() if args.output else root / f"handoff-{state['current_state'].lower()}.json"
    write_json(destination, handoff_template(state))
    handoff_id, created_at = make_id("handoff"), now()
    state["metrics"]["handoff_count"] += 1
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        connection.execute("INSERT INTO handoffs VALUES(?,?,?,?,?)", (handoff_id, state["run_id"], state["current_state"], created_at, str(destination)))
    append_jsonl(root / "events.jsonl", {"event": "HANDOFF_CREATED", "at": created_at, "run_id": state["run_id"], "handoff_id": handoff_id, "stage": state["current_state"]})
    persist_state(root, state)
    return {"handoff": str(destination), "handoff_id": handoff_id}


def validate_handoff_data(data: dict[str, Any]) -> list[str]:
    schema = load_json(ROOT / "contracts/handoff.schema.json")
    errors: list[str] = []
    missing, extra = set(schema["required"]) - set(data), set(data) - set(schema["properties"])
    if missing: errors.append(f"campos ausentes: {sorted(missing)}")
    if extra: errors.append(f"campos não permitidos: {sorted(extra)}")
    for field in ("status", "stage", "complexity", "risk_class", "operational_mode", "reasoning_class", "stop_reason"):
        if field in data and data[field] not in schema["properties"][field]["enum"]: errors.append(f"{field} inválido: {data[field]!r}")
    if data.get("schema_version") != "2.0.0": errors.append("schema_version deve ser 2.0.0")
    requirements = data.get("requirement_ids", [])
    for index, item in enumerate(data.get("files", [])):
        if not isinstance(item, dict): errors.append(f"files[{index}] não é objeto"); continue
        for field in ("path", "purpose", "requirement_ids", "owner"):
            if not item.get(field): errors.append(f"files[{index}] sem {field}")
        unknown = set(item.get("requirement_ids", [])) - set(requirements)
        if unknown: errors.append(f"files[{index}] referencia requisitos ausentes do handoff: {sorted(unknown)}")
    validations = data.get("validations", {})
    if not isinstance(validations, dict) or set(validations) != {"executed", "passed", "failed", "not_executed"}: errors.append("validations deve declarar executed, passed, failed e not_executed")
    if data.get("status") in {"BLOCKED", "NEEDS_EXPLANATION"} and not data.get("stop_reason"): errors.append("status bloqueante exige stop_reason")
    if data.get("risk_class") in {"HIGH", "CRITICAL"} and data.get("status") in {"READY_FOR_REVIEW", "DONE"} and not data.get("decisions"): errors.append("handoff HIGH/CRITICAL pronto exige provenance em decisions")
    try: assert_safe_metadata(data)
    except RuntimeErrorSafe as exc: errors.append(str(exc))
    return errors


def validate_handoff(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path).resolve()
    errors = validate_handoff_data(load_json(path))
    if errors: raise RuntimeErrorSafe("handoff inválido: " + "; ".join(errors))
    return {"valid": True, "path": str(path)}


def _safe_text(value: Any, fallback: str = "UNKNOWN/NOT_CONFIRMED") -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _evidence_items(items: Any, workspace_root: Path) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for raw in items if isinstance(items, list) else []:
        if not isinstance(raw, dict):
            continue
        relative = raw.get("path")
        symbol = raw.get("symbol")
        status = "UNKNOWN"
        if isinstance(relative, str) and relative.strip() and isinstance(symbol, str) and symbol.strip():
            candidate = Path(relative)
            candidate = candidate if candidate.is_absolute() else workspace_root / candidate
            try:
                status = "CONFIRMED" if candidate.is_file() and symbol in candidate.read_text(encoding="utf-8", errors="ignore") else "UNKNOWN"
            except OSError:
                status = "UNKNOWN"
        normalized.append({
            "description": _safe_text(raw.get("description")),
            "path": relative.strip() if isinstance(relative, str) and relative.strip() else None,
            "symbol": symbol.strip() if isinstance(symbol, str) and symbol.strip() else None,
            "reason": _safe_text(raw.get("reason"), "Evidência não confirmada no workspace informado."),
            "evidence_status": status,
        })
    return normalized


def _concepts(value: str, limit: int = 3) -> list[str]:
    words = re.findall(r"[A-Za-zÀ-ÿ_][A-Za-zÀ-ÿ0-9_.#-]{2,}", value)
    ignored = {"para", "como", "com", "uma", "das", "dos", "que", "the", "and", "UNKNOWN", "NOT_CONFIRMED"}
    result: list[str] = []
    for word in words:
        if word.lower() not in {item.lower() for item in ignored} and word.lower() not in {item.lower() for item in result}:
            result.append(word)
        if len(result) == limit:
            break
    return result or ["evidência"]


def _question_generator(handoff: dict[str, Any], count: int) -> list[dict[str, Any]]:
    if count == 0:
        return []
    confirmed = [item for item in handoff["reading_order"] if item["evidence_status"] == "CONFIRMED"]
    tests = [item for item in handoff["test_evidence"] if item["evidence_status"] == "CONFIRMED"]
    decisions = [item for item in handoff["decisions"] if item["evidence_status"] == "CONFIRMED"]
    risks = [item for item in handoff["risks"] if item["evidence_status"] == "CONFIRMED"]
    sources = [
        ("Qual símbolo concentra a mudança principal?", confirmed[0] if confirmed else None),
        ("Por que essa decisão técnica foi adotada?", decisions[0] if decisions else (confirmed[0] if confirmed else None)),
        ("Qual teste protege a regressão principal?", tests[0] if tests else None),
        ("Onde você começaria uma nova investigação dessa regra?", confirmed[0] if confirmed else None),
        ("Qual risco ou invariante não pode ser quebrado?", risks[0] if risks else None),
    ]
    questions: list[dict[str, Any]] = []
    for index, (prompt, item) in enumerate(sources[:count], start=1):
        evidence_ref = "UNKNOWN/NOT_CONFIRMED"
        concept_source = handoff["summary"]
        if item:
            evidence_ref = f"{item['path']}#{item['symbol']}"
            concept_source = " ".join(filter(None, (item["symbol"], item["description"])))
        questions.append({"question_id": f"Q{index}", "prompt": prompt, "expected_concepts": _concepts(concept_source), "evidence_refs": [evidence_ref]})
    return questions


def validate_technical_handoff_data(data: dict[str, Any]) -> list[str]:
    schema = load_json(ROOT / "contracts/technical-handoff.schema.json")
    errors: list[str] = []
    missing = set(schema["required"]) - set(data)
    extra = set(data) - set(schema["properties"])
    if missing:
        errors.append(f"campos ausentes: {sorted(missing)}")
    if extra:
        errors.append(f"campos não permitidos: {sorted(extra)}")
    if data.get("schema_version") != "1.0.0":
        errors.append("schema_version deve ser 1.0.0")
    if data.get("classification") not in KNOWLEDGE_TRANSFER_CLASSES[1:]:
        errors.append("classification inválida")
    if data.get("evidence_status") not in EVIDENCE_STATUSES:
        errors.append("evidence_status inválido")
    for section in ("changed_components", "execution_flow", "decisions", "risks", "test_evidence", "reading_order"):
        if not isinstance(data.get(section), list):
            errors.append(f"{section} deve ser lista")
            continue
        for index, item in enumerate(data[section]):
            if not isinstance(item, dict) or set(item) != {"description", "path", "symbol", "reason", "evidence_status"}:
                errors.append(f"{section}[{index}] inválido")
    for index, question in enumerate(data.get("questions", [])):
        expected = {"question_id", "prompt", "expected_concepts", "evidence_refs"}
        if not isinstance(question, dict) or set(question) != expected or not question.get("expected_concepts") or not question.get("evidence_refs"):
            errors.append(f"questions[{index}] inválida")
    return errors


@locked_run
def create_technical_handoff(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    decision = knowledge_transfer_decision(state)
    if not decision["enabled"]:
        return {"enabled": False, "classification": decision["classification"], "reason": "policy disables handoff for trivial changes"}
    observed_tokens = int(getattr(args, "handoff_tokens", 0) or 0)
    if observed_tokens > decision["max_handoff_tokens"]:
        raise RuntimeErrorSafe("handoff excede max_handoff_tokens")
    spec = load_json(Path(args.input).resolve())
    assert_safe_metadata(spec)
    workspace_root = Path(getattr(args, "workspace_root", None) or ROOT).resolve()
    sections = {name: _evidence_items(spec.get(name, []), workspace_root) for name in (
        "changed_components", "execution_flow", "decisions", "risks", "test_evidence", "reading_order"
    )}
    if not sections["reading_order"]:
        sections["reading_order"] = sorted(
            sections["changed_components"] + sections["test_evidence"],
            key=lambda item: ("test" in (item["path"] or "").lower(), item["path"] or ""),
        )
    statuses = [item["evidence_status"] for values in sections.values() for item in values]
    evidence_status = "CONFIRMED" if statuses and all(item == "CONFIRMED" for item in statuses) else "PARTIAL" if "CONFIRMED" in statuses else "UNKNOWN"
    handoff_id = make_id("technical-handoff")
    execution_id = spec.get("execution_id")
    handoff = {
        "schema_version": "1.0.0", "policy_version": decision["policy_version"],
        "handoff_id": handoff_id, "task_id": state["task_id"], "run_id": state["run_id"],
        "execution_id": execution_id, "classification": decision["classification"],
        "handoff_level": decision["handoff"], "summary": _safe_text(spec.get("summary")),
        "previous_behavior": _safe_text(spec.get("previous_behavior")),
        "new_behavior": _safe_text(spec.get("new_behavior")), **sections,
        "questions": [], "evidence_status": evidence_status, "created_at": now(),
    }
    supplied_questions = spec.get("questions") if isinstance(spec.get("questions"), list) else []
    question_limit = decision["teach_back_questions"]
    if supplied_questions:
        confirmed_refs = {f"{item['path']}#{item['symbol']}" for values in sections.values() for item in values if item["evidence_status"] == "CONFIRMED"}
        for index, item in enumerate(supplied_questions[:question_limit], start=1):
            if not isinstance(item, dict):
                continue
            refs = sorted(set(item.get("evidence_refs", []))) & confirmed_refs
            concepts = sorted({_safe_text(value) for value in item.get("expected_concepts", []) if _safe_text(value) != "UNKNOWN/NOT_CONFIRMED"})
            handoff["questions"].append({"question_id": _safe_text(item.get("question_id"), f"Q{index}"), "prompt": _safe_text(item.get("prompt")), "expected_concepts": concepts or _concepts(handoff["summary"]), "evidence_refs": sorted(refs) or ["UNKNOWN/NOT_CONFIRMED"]})
    else:
        handoff["questions"] = _question_generator(handoff, question_limit)
    errors = validate_technical_handoff_data(handoff)
    if errors:
        raise RuntimeErrorSafe("technical handoff inválido: " + "; ".join(errors))
    destination = Path(args.output).resolve() if getattr(args, "output", None) else root / "technical-handoff.json"
    write_json(destination, handoff)
    duration_ms = int(getattr(args, "duration_ms", 0) or 0)
    with connect_db(telemetry_db_for_state(state, root)) as connection:
        connection.execute(
            """INSERT INTO technical_handoffs(handoff_id,task_id,run_id,execution_id,classification,summary,previous_behavior,new_behavior,reading_map_json,decisions_json,risks_json,test_evidence_json,output_path,created_at,policy_version,evidence_status,handoff_tokens,handoff_duration_ms,teachback_required,teachback_questions) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (handoff_id, state["task_id"], state["run_id"], execution_id, decision["classification"], handoff["summary"], handoff["previous_behavior"], handoff["new_behavior"], json.dumps(handoff["reading_order"], ensure_ascii=False), json.dumps(handoff["decisions"], ensure_ascii=False), json.dumps(handoff["risks"], ensure_ascii=False), json.dumps(handoff["test_evidence"], ensure_ascii=False), str(destination), handoff["created_at"], decision["policy_version"], evidence_status, observed_tokens, duration_ms, int(decision["teach_back_required"]), len(handoff["questions"])),
        )
    append_jsonl(root / "events.jsonl", {"event": "TECHNICAL_HANDOFF_GENERATED", "at": handoff["created_at"], "run_id": state["run_id"], "handoff_id": handoff_id, "classification": decision["classification"], "evidence_status": evidence_status, "teachback_required": decision["teach_back_required"], "teachback_questions": len(handoff["questions"]), "handoff_tokens": observed_tokens, "handoff_duration_ms": duration_ms})
    return {"enabled": True, "technical_handoff": str(destination), "handoff_id": handoff_id, "classification": decision["classification"], "handoff_level": decision["handoff"], "evidence_status": evidence_status, "teachback_required": decision["teach_back_required"], "teachback_questions": len(handoff["questions"])}


def get_technical_handoff(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.telemetry_db).resolve()
    if not db_path.is_file():
        raise RuntimeErrorSafe(f"banco de telemetria ausente: {db_path}")
    with connect_db(db_path) as connection:
        row = connection.execute("SELECT output_path FROM technical_handoffs WHERE task_id=? ORDER BY created_at DESC LIMIT 1", (args.task_id,)).fetchone()
    if row is None:
        raise RuntimeErrorSafe("technical handoff não encontrado para a task")
    path = Path(row["output_path"])
    if not path.is_file():
        raise RuntimeErrorSafe("artefato do technical handoff não está mais disponível")
    return load_json(path)


def evaluate_teachback(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.telemetry_db).resolve()
    if not db_path.is_file():
        raise RuntimeErrorSafe(f"banco de telemetria ausente: {db_path}")
    with connect_db(db_path) as connection:
        row = connection.execute("SELECT task_id,run_id,output_path FROM technical_handoffs WHERE handoff_id=?", (args.handoff_id,)).fetchone()
        if row is None:
            raise RuntimeErrorSafe("technical handoff inexistente")
        handoff = load_json(Path(row["output_path"]))
        question = next((item for item in handoff["questions"] if item["question_id"] == args.question_id), None)
        if question is None:
            raise RuntimeErrorSafe("pergunta inexistente no technical handoff")
        turns = connection.execute("SELECT COUNT(*) FROM teachback_evaluations WHERE handoff_id=?", (args.handoff_id,)).fetchone()[0]
        maximum = load_knowledge_transfer_policy()["budget"]["max_teachback_turns"]
        if turns >= maximum:
            raise RuntimeErrorSafe("teach-back excede max_teachback_turns")
        answer = args.answer.casefold()
        concepts = question["expected_concepts"]
        matched = sum(concept.casefold() in answer for concept in concepts)
        ratio = matched / len(concepts)
        result = "CORRECT" if ratio >= .75 else "PARTIAL" if ratio >= .35 else "INCORRECT"
        evaluation_id = make_id("teachback")
        created_at = now()
        connection.execute(
            """INSERT INTO teachback_evaluations(evaluation_id,handoff_id,task_id,question_id,result,matched_concepts,total_concepts,duration_ms,developer_requested_deeper_explanation,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (evaluation_id, args.handoff_id, row["task_id"], args.question_id, result, matched, len(concepts), int(getattr(args, "duration_ms", 0) or 0), int(bool(getattr(args, "deeper_explanation", False))), created_at),
        )
    append_jsonl(Path(row["output_path"]).parent / "events.jsonl", {"event": "TEACHBACK_EVALUATED", "at": created_at, "run_id": row["run_id"], "handoff_id": args.handoff_id, "question_id": args.question_id, "result": result, "matched_concepts": matched, "total_concepts": len(concepts), "duration_ms": int(getattr(args, "duration_ms", 0) or 0), "developer_requested_deeper_explanation": bool(getattr(args, "deeper_explanation", False))})
    response = {"evaluation_id": evaluation_id, "result": result, "matched_concepts": matched, "total_concepts": len(concepts), "evidence_refs": question["evidence_refs"] if result != "CORRECT" else []}
    if result == "PARTIAL":
        response["guidance"] = "Explique somente os conceitos que faltaram e tente novamente."
    elif result == "INCORRECT":
        response["guidance"] = "Revise as evidências indicadas e responda novamente com suas palavras."
    return response


def context_pack(args: argparse.Namespace) -> dict[str, Any]:
    root, refs = run_path(args.run_dir), sorted(set(args.ref))
    state = load_json(root / "state.json")
    assert_safe_metadata(refs, "evidence_refs")
    payload = {"schema_version": 1, "run_id": state["run_id"], "kind": args.kind, "created_at": now(), "baseline": args.baseline, "evidence_refs": refs, "content_policy": "references_and_hashes_only"}
    destination = root / "context-packs" / f"{args.kind}.json"
    write_json(destination, payload)
    return {"context_pack": str(destination), "refs": len(refs)}


def discovery_record(args: argparse.Namespace) -> dict[str, Any]:
    root, refs = run_path(args.run_dir), sorted(set(args.ref))
    state = load_json(root / "state.json")
    assert_safe_metadata(refs, "evidence_refs")
    event = {"schema_version": 1, "run_id": state["run_id"], "at": now(), "baseline": args.baseline, "query_hash": hashlib.sha256(args.query.encode()).hexdigest(), "evidence_refs": refs, "note": "facts_only_not_conclusions"}
    append_jsonl(root / "discovery-cache.jsonl", event)
    return {"query_hash": event["query_hash"], "refs": len(refs)}


def summary(args: argparse.Namespace) -> dict[str, Any]:
    state = load_json(run_path(args.run_dir) / "state.json")
    return {"run_id": state["run_id"], "jarvis_version": state["jarvis_version"], "task_id": state["task_id"], "state": state["current_state"], "complexity": state["complexity"], "risk_class": state["risk_class"], "operational_mode": state["operational_mode"], "reasoning_class": state["reasoning_class"], "reasoning": state.get("reasoning"), "agents": state["agents_used"], "unique_agent_count": len(state["agents_used"]), "budget": state["budget"], "routing": state["routing"], "metrics": state["metrics"], "gate_decision": state["gate_decision"], "gate_reason_code": state["gate_reason_code"], "gate_attempts": state["gate_attempts"]}


def percentile(values: list[int], fraction: float) -> int:
    if not values: return 0
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def group_sum(rows: list[dict[str, Any]], group: str, value: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in rows: result[row[group]] = result.get(row[group], 0) + row[value]
    return dict(sorted(result.items()))


def release_eval(args: argparse.Namespace) -> dict[str, Any]:
    versions = load_json(VERSION_PATH)
    values = {key: getattr(args, key) for key in ("routing_score", "over_routing_score", "under_routing_score", "sequence_score")}
    for key, value in values.items():
        if not 0 <= value <= 1:
            raise RuntimeErrorSafe(f"{key} deve estar entre 0 e 1")
    payload = {
        "eval_id": getattr(args, "eval_id", None) or make_id("eval"),
        "jarvis_version": getattr(args, "jarvis_version", None) or versions["jarvis_version"],
        "config_hash": getattr(args, "config_hash", None) or config_hash(), "evaluated_at": now(),
        **values, "source_ref": getattr(args, "source_ref", None),
    }
    assert_safe_metadata(payload)
    with connect_db(Path(args.telemetry_db).resolve()) as connection:
        connection.execute("INSERT INTO release_evals VALUES(?,?,?,?,?,?,?,?,?)", tuple(payload.values()))
    return payload


def compare_releases(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.telemetry_db).resolve()
    if not db_path.is_file():
        raise RuntimeErrorSafe(f"banco de telemetria ausente: {db_path}")
    with connect_db(db_path) as connection:
        runs = [dict(row) for row in connection.execute("SELECT * FROM runs")]
        evals = [dict(row) for row in connection.execute("SELECT * FROM release_evals ORDER BY evaluated_at")]
    groups: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        key = f"{run['jarvis_version']}:{run['config_hash'][:12]}"
        groups.setdefault(key, []).append(run)
    comparison = {}
    for key, items in sorted(groups.items()):
        count = len(items)
        comparison[key] = {
            "jarvis_version": items[0]["jarvis_version"], "config_hash": items[0]["config_hash"],
            "total_runs": count, "success_rate": sum(item["status"] == "DONE" for item in items) / count,
            "first_pass_success_rate": sum(item["first_pass_success"] == 1 for item in items) / count,
            "average_duration_ms": sum(item["duration_ms"] for item in items) / count,
            "average_credits": sum(item["credits"] for item in items) / count,
            "average_rework_cycles": sum(item["rework_cycles"] for item in items) / count,
            "over_routing_rate": sum(item["routing_outcome"] == "OVER_ROUTED" for item in items) / count,
            "under_routing_rate": sum(item["routing_outcome"] == "UNDER_ROUTED" for item in items) / count,
        }
    return {"telemetry_db": str(db_path), "releases": comparison, "eval_results": evals}


def dashboard(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(getattr(args, "telemetry_db", None) or telemetry_db_for_runs(Path(args.runs_dir))).resolve()
    if not db_path.is_file(): return {"telemetry_db": str(db_path), "total_runs": 0}
    with connect_db(db_path) as connection:
        runs = [dict(row) for row in connection.execute("SELECT * FROM runs")]
        invocations = [dict(row) for row in connection.execute("SELECT * FROM agent_invocations")]
        findings = [dict(row) for row in connection.execute("SELECT * FROM findings")]
        gates = [dict(row) for row in connection.execute("SELECT * FROM human_gates")]
        attempts = [dict(row) for row in connection.execute("SELECT * FROM execution_attempts")]
        technical_handoffs = [dict(row) for row in connection.execute("SELECT * FROM technical_handoffs")]
        teachback = [dict(row) for row in connection.execute("SELECT * FROM teachback_evaluations")]
        stops = [row[0] for row in connection.execute("SELECT stop_reason FROM transitions WHERE stop_reason IS NOT NULL")]
    total, durations = len(runs), [row["duration_ms"] for row in runs]
    agents: dict[str, dict[str, int | float]] = {}
    for inv in invocations:
        item = agents.setdefault(inv["agent"], {"invocations": 0, "with_findings": 0, "actionable_findings": 0, "credits": 0.0})
        item["invocations"] += 1; item["credits"] += inv["credits"]; item["with_findings"] += int(inv["findings_count"] > 0)
    invocation_agents = {item["invocation_id"]: item["agent"] for item in invocations}
    actionable_invocations = {item["invocation_id"] for item in findings if item["actioned"]}
    for invocation_id in actionable_invocations:
        agents[invocation_agents[invocation_id]]["actionable_findings"] += 1
    agent_metrics = {name: {**value, "finding_rate": value["with_findings"] / value["invocations"], "actionable_finding_rate": value["actionable_findings"] / value["invocations"]} for name, value in sorted(agents.items())}
    approved = {row["run_id"] for row in gates if row["decision"] == "APPROVED"}
    completed_attempts = [row for row in attempts if row["success"] is not None]
    calls_by_context = {budget: sum(row["context_budget"] == budget for row in attempts) for budget in CONTEXT_BUDGETS}
    return {"telemetry_db": str(db_path), "total_runs": total, "successful_runs": sum(row["status"] == "DONE" for row in runs), "failed_runs": sum(row["status"] == "BLOCKED" for row in runs), "average_duration_ms": sum(durations) / total if total else 0, "p50_duration_ms": percentile(durations, .5), "p95_duration_ms": percentile(durations, .95), "first_pass_success_rate": sum(row["first_pass_success"] == 1 for row in runs) / total if total else 0, "human_approval_rate": len(approved) / total if total else 0, "average_rework_cycles": sum(row["rework_cycles"] for row in runs) / total if total else 0, "average_credits": sum(row["credits"] for row in runs) / total if total else 0, "average_agent_invocations": sum(row["agent_invocation_count"] for row in runs) / total if total else 0, "average_unique_agents": sum(row["unique_agent_count"] for row in runs) / total if total else 0, "over_budget_rate": sum(row["budget_override"] == 1 for row in runs) / total if total else 0, "over_routing_rate": sum(row["routing_outcome"] == "OVER_ROUTED" for row in runs) / total if total else 0, "under_routing_rate": sum(row["routing_outcome"] == "UNDER_ROUTED" for row in runs) / total if total else 0, "credits_by_complexity": group_sum(runs, "complexity", "credits"), "credits_by_risk": group_sum(runs, "risk_class", "credits"), "credits_by_agent": group_sum(invocations, "agent", "credits"), "credits_by_model": group_sum(invocations, "model", "credits"), "credits_by_reasoning_effort": group_sum(invocations, "reasoning_effort", "credits"), "calls_by_context_budget": calls_by_context, "uncached_input_tokens": sum(max(0, row["input_tokens"] - row["cached_input_tokens"]) for row in attempts), "progress_event_count": sum(bool(row["progress_event"]) for row in attempts), "attempts_by_reasoning": {level: sum(row["effective_reasoning"] == level for row in attempts) for level in REASONING_LEVELS}, "success_rate_by_reasoning": {level: (sum(row["effective_reasoning"] == level and row["success"] == 1 for row in completed_attempts) / max(1, sum(row["effective_reasoning"] == level for row in completed_attempts))) for level in REASONING_LEVELS}, "credits_by_reasoning": group_sum(attempts, "effective_reasoning", "credits"), "escalation_count": sum(row["escalated"] == 1 for row in attempts), "handoff_generated": len(technical_handoffs), "handoff_tokens": sum(row["handoff_tokens"] for row in technical_handoffs), "handoff_duration_ms": sum(row["handoff_duration_ms"] for row in technical_handoffs), "handoff_levels": {level: sum(row["classification"] == level for row in technical_handoffs) for level in KNOWLEDGE_TRANSFER_CLASSES[1:]}, "teachback_required": sum(row["teachback_required"] for row in technical_handoffs), "teachback_questions": sum(row["teachback_questions"] for row in technical_handoffs), "teachback_correct": sum(row["result"] == "CORRECT" for row in teachback), "teachback_partial": sum(row["result"] == "PARTIAL" for row in teachback), "teachback_incorrect": sum(row["result"] == "INCORRECT" for row in teachback), "teachback_duration_ms": sum(row["duration_ms"] for row in teachback), "developer_requested_deeper_explanation": sum(row["developer_requested_deeper_explanation"] for row in teachback), "agent_metrics": agent_metrics, "stop_reason_distribution": {reason: stops.count(reason) for reason in STOP_REASONS}, "human_rejection_reason_distribution": {code: sum(row["reason_code"] == code for row in gates if row["decision"] != "APPROVED") for code in GATE_REASON_CODES if code != "APPROVED_AS_PLANNED"}}


def report_cost(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(getattr(args, "telemetry_db", None) or telemetry_db_for_runs(Path(args.runs_dir))).resolve()
    if not db_path.is_file():
        raise RuntimeErrorSafe(f"banco de telemetria ausente: {db_path}")
    with connect_db(db_path) as connection:
        if args.run_id:
            runs = [dict(row) for row in connection.execute("SELECT * FROM runs WHERE run_id=? OR task_id=? ORDER BY started_at DESC", (args.run_id, args.run_id))]
        else:
            runs = [dict(row) for row in connection.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (args.last,))]
        if not runs:
            raise RuntimeErrorSafe("nenhuma execução encontrada para o relatório de custo")
        run_ids = [row["run_id"] for row in runs]
        placeholders = ",".join("?" for _ in run_ids)
        invocations = [dict(row) for row in connection.execute(f"SELECT * FROM agent_invocations WHERE run_id IN ({placeholders})", run_ids)]
        attempts = [dict(row) for row in connection.execute(f"SELECT * FROM execution_attempts WHERE run_id IN ({placeholders})", run_ids)]

    def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
        input_tokens = sum(item["input_tokens"] for item in items)
        cached = sum(item["cached_input_tokens"] for item in items)
        output = sum(item["output_tokens"] for item in items)
        credits = sum(item["credits"] for item in items)
        return {"calls": len(items), "input_tokens": input_tokens, "cached_input_tokens": cached, "uncached_input_tokens": max(0, input_tokens - cached), "output_tokens": output, "credits": round(credits, 4), "cache_hit_ratio": cached / input_tokens if input_tokens else 0.0}

    grouped: dict[str, list[dict[str, Any]]] = {}
    group_field = "agent" if args.group_by == "agent" else "stage"
    for item in invocations:
        grouped.setdefault(item[group_field], []).append(item)
    group_summary = {key: summarize(items) for key, items in grouped.items()}
    selected_attempts = [item for item in attempts if item["finished_at"] is not None]
    retry_attempts = [item for item in selected_attempts if item["attempt_number"] > 1]
    total_credits = sum(item["credits"] for item in selected_attempts)
    retry_credits = sum(item["credits"] for item in retry_attempts)
    files_changed = sum(item["files_changed"] for item in selected_attempts)
    top_stages: dict[str, float] = {}
    for item in invocations:
        top_stages[item["stage"]] = top_stages.get(item["stage"], 0.0) + item["credits"]
    return {
        "telemetry_db": str(db_path),
        "runs": [{key: row[key] for key in ("run_id", "task_id", "status", "complexity", "risk_class", "reasoning_class", "credits")} for row in runs],
        "totals": {**summarize(invocations), "unique_agents": len({item["agent"] for item in invocations}), "credits_per_file_changed": total_credits / files_changed if files_changed else None, "retry_credit_ratio": retry_credits / total_credits if total_credits else 0.0},
        f"by_{args.group_by}": dict(sorted(group_summary.items(), key=lambda item: item[1]["credits"], reverse=True)),
        "top_stages": [{"stage": stage, "credits": round(credits, 4)} for stage, credits in sorted(top_stages.items(), key=lambda item: item[1], reverse=True)[:3]],
    }


EXPORT_TABLES = ("runs", "agent_invocations", "execution_attempts", "transitions", "handoffs", "technical_handoffs", "teachback_evaluations", "findings", "human_gates", "decisions", "routing_snapshots", "release_evals")


def export_telemetry(args: argparse.Namespace) -> dict[str, Any]:
    db_path, output = Path(args.telemetry_db).resolve(), Path(args.output).resolve()
    if not db_path.is_file(): raise RuntimeErrorSafe(f"banco de telemetria ausente: {db_path}")
    with connect_db(db_path) as connection:
        data = {table: [dict(row) for row in connection.execute(f"SELECT * FROM {table}")] for table in EXPORT_TABLES}
        columns = {table: [row[1] for row in connection.execute(f"PRAGMA table_info({table})")] for table in EXPORT_TABLES}
    if args.format == "json":
        write_json(output, {"schema_version": load_json(VERSION_PATH)["telemetry_schema_version"], "exported_at": now(), "tables": data})
    else:
        output.mkdir(parents=True, exist_ok=True)
        for table, rows in data.items():
            with (output / f"{table}.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=columns[table]); writer.writeheader(); writer.writerows(rows)
    return {"format": args.format, "output": str(output), "rows": {table: len(rows) for table, rows in data.items()}}


def add_signal_arguments(target: argparse.ArgumentParser) -> None:
    target.add_argument("--task-type", default="GENERAL")
    target.add_argument("--estimated-files", type=int, default=0)
    target.add_argument("--estimated-modules", type=int, default=0)
    target.add_argument("--architectural", action="store_true")
    target.add_argument("--production-critical", action="store_true")
    target.add_argument("--database-migration", action="store_true")
    target.add_argument("--security-sensitive", action="store_true")
    target.add_argument("--tests-required", action="store_true")
    target.add_argument("--ambiguity-score", type=float, default=0)
    target.add_argument("--complexity-score", type=float, default=0)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    decide = sub.add_parser("reasoning-decide"); add_signal_arguments(decide)
    init = sub.add_parser("init"); init.add_argument("--task-id", required=True); init.add_argument("--complexity", choices=COMPLEXITIES, required=True); init.add_argument("--risk-class", choices=RISKS, required=True); init.add_argument("--operational-mode", choices=MODES, required=True); init.add_argument("--reasoning-class", choices=REASONING); init.add_argument("--budget-justification"); init.add_argument("--agent-planned", action="append", dest="agents_planned", default=[]); init.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR); init.add_argument("--telemetry-db", type=Path); add_signal_arguments(init)
    move = sub.add_parser("transition"); move.add_argument("--run-dir", required=True); move.add_argument("--to", choices=STATES, required=True); move.add_argument("--reason", required=True); move.add_argument("--stop-reason", choices=STOP_REASONS); move.add_argument("--gate-decision", choices=GATE_DECISIONS); move.add_argument("--gate-reason-code", choices=GATE_REASON_CODES); move.add_argument("--gate-reason-detail"); move.add_argument("--rework-origin", choices=REWORK_ORIGINS); move.add_argument("--rework-reason", choices=REWORK_REASONS)
    start = sub.add_parser("invocation-start"); start.add_argument("--run-dir", required=True); start.add_argument("--invocation-id"); start.add_argument("--agent", required=True); start.add_argument("--stage", choices=STATES, required=True); start.add_argument("--model"); start.add_argument("--reasoning-effort", choices=REASONING_EFFORTS); start.add_argument("--attempt-number", type=int); start.add_argument("--task-type"); start.add_argument("--parent-execution-id"); start.add_argument("--child-depth", type=int, default=0); start.add_argument("--progress-event", choices=PROGRESS_EVENTS); start.add_argument("--parallel-batch"); start.add_argument("--budget-justification")
    finish = sub.add_parser("invocation-finish"); finish.add_argument("--run-dir", required=True); finish.add_argument("--invocation-id", required=True); finish.add_argument("--status", required=True); finish.add_argument("--agent-result", choices=AGENT_RESULTS, required=True); finish.add_argument("--model-effective"); finish.add_argument("--reasoning-effort-effective", choices=REASONING_EFFORTS); finish.add_argument("--input-tokens", type=int, default=0); finish.add_argument("--cached-input-tokens", type=int, default=0); finish.add_argument("--output-tokens", type=int, default=0); finish.add_argument("--credits", type=float, default=0); finish.add_argument("--retry-count", type=int, default=0); finish.add_argument("--files-read", type=int, default=0); finish.add_argument("--files-changed", type=int, default=0); finish.add_argument("--tool-calls", type=int, default=0); finish.add_argument("--tests-run", type=int, default=0); finish.add_argument("--tests-passed", type=int, default=0); finish.add_argument("--tests-failed", type=int, default=0); finish.add_argument("--review-findings", type=int, default=0); finish.add_argument("--success", action=argparse.BooleanOptionalAction); finish.add_argument("--termination-reason", choices=TERMINATION_REASONS); finish.add_argument("--blocker")
    evaluate = sub.add_parser("evaluate"); evaluate.add_argument("--run-dir", required=True); evaluate.add_argument("--success", action=argparse.BooleanOptionalAction, required=True); evaluate.add_argument("--escalation-reason", choices=ESCALATION_REASONS); evaluate.add_argument("--previous-execution-id"); evaluate.add_argument("--changed-file", action="append", dest="changed_files"); evaluate.add_argument("--tests-failed", type=int, default=0); evaluate.add_argument("--failed-hypotheses-count", type=int, default=0)
    item = sub.add_parser("record"); item.add_argument("--run-dir", required=True); item.add_argument("--stage", choices=STATES, required=True); item.add_argument("--agent"); item.add_argument("--status", required=True); item.add_argument("--reasoning-class", choices=REASONING); item.add_argument("--model", default="unknown"); item.add_argument("--reasoning-effort", choices=REASONING_EFFORTS); item.add_argument("--started-at"); item.add_argument("--finished-at"); item.add_argument("--duration-ms", type=int); item.add_argument("--input-tokens", type=int, default=0); item.add_argument("--cached-input-tokens", type=int, default=0); item.add_argument("--output-tokens", type=int, default=0); item.add_argument("--credits", type=float); item.add_argument("--token-or-credit-cost", type=float, default=0); item.add_argument("--agent-result", choices=AGENT_RESULTS); item.add_argument("--findings-count", type=int, default=0); item.add_argument("--critical-findings-count", type=int, default=0); item.add_argument("--parallel-batch"); item.add_argument("--retry-count", type=int, default=0); item.add_argument("--blocker"); item.add_argument("--budget-justification")
    fp = sub.add_parser("finding"); fp.add_argument("--run-dir", required=True); fp.add_argument("--finding-id"); fp.add_argument("--invocation-id", required=True); fp.add_argument("--category", required=True); fp.add_argument("--severity", choices=FINDING_SEVERITIES, required=True); fp.add_argument("--actioned", action=argparse.BooleanOptionalAction, required=True); fp.add_argument("--evidence-ref")
    routing = sub.add_parser("route"); routing.add_argument("--run-dir", required=True); routing.add_argument("--routing-outcome", choices=ROUTING_OUTCOMES, required=True); routing.add_argument("--agent-planned", action="append", dest="agents_planned"); routing.add_argument("--agent-skipped", action="append", dest="agents_skipped"); routing.add_argument("--agent-rejected-by-budget", action="append", dest="agents_rejected_by_budget"); routing.add_argument("--unnecessary-agent", action="append", dest="unnecessary_agents"); routing.add_argument("--missing-agent", action="append", dest="missing_agents")
    provenance = sub.add_parser("decision"); provenance.add_argument("--run-dir", required=True); provenance.add_argument("--decision-id"); provenance.add_argument("--agent", required=True); provenance.add_argument("--category", required=True); provenance.add_argument("--decision", required=True); provenance.add_argument("--evidence-ref", action="append", required=True); provenance.add_argument("--confidence", choices=("LOW", "MEDIUM", "HIGH"), required=True); provenance.add_argument("--confirmed-by"); provenance.add_argument("--challenged-by"); provenance.add_argument("--overridden-by")
    handoff = sub.add_parser("handoff"); handoff.add_argument("--run-dir", required=True); handoff.add_argument("--output")
    hv = sub.add_parser("validate-handoff"); hv.add_argument("path")
    technical = sub.add_parser("technical-handoff"); technical.add_argument("--run-dir", required=True); technical.add_argument("--input", required=True); technical.add_argument("--workspace-root"); technical.add_argument("--output"); technical.add_argument("--handoff-tokens", type=int, default=0); technical.add_argument("--duration-ms", type=int, default=0)
    technical_get = sub.add_parser("technical-handoff-get"); technical_get.add_argument("--task-id", required=True); technical_get.add_argument("--telemetry-db", type=Path, default=DEFAULT_TELEMETRY_DB)
    teachback = sub.add_parser("teachback-evaluate"); teachback.add_argument("--handoff-id", required=True); teachback.add_argument("--question-id", required=True); teachback.add_argument("--answer", required=True); teachback.add_argument("--duration-ms", type=int, default=0); teachback.add_argument("--deeper-explanation", action="store_true"); teachback.add_argument("--telemetry-db", type=Path, default=DEFAULT_TELEMETRY_DB)
    pack = sub.add_parser("context-pack"); pack.add_argument("--run-dir", required=True); pack.add_argument("--kind", choices=("requirement", "database", "contract", "git-baseline"), required=True); pack.add_argument("--baseline", required=True); pack.add_argument("--ref", action="append", required=True)
    discovery = sub.add_parser("discovery"); discovery.add_argument("--run-dir", required=True); discovery.add_argument("--baseline", required=True); discovery.add_argument("--query", required=True); discovery.add_argument("--ref", action="append", required=True)
    sm = sub.add_parser("summary"); sm.add_argument("--run-dir", required=True)
    metrics = sub.add_parser("dashboard"); metrics.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR); metrics.add_argument("--telemetry-db", type=Path)
    cost_report = sub.add_parser("report-cost"); cost_report.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR); cost_report.add_argument("--telemetry-db", type=Path); cost_report.add_argument("--run-id"); cost_report.add_argument("--last", type=int, default=20); cost_report.add_argument("--group-by", choices=("agent", "stage"), default="agent")
    eval_parser = sub.add_parser("eval-result"); eval_parser.add_argument("--telemetry-db", type=Path, default=DEFAULT_TELEMETRY_DB); eval_parser.add_argument("--eval-id"); eval_parser.add_argument("--jarvis-version"); eval_parser.add_argument("--config-hash"); eval_parser.add_argument("--routing-score", type=float, required=True); eval_parser.add_argument("--over-routing-score", type=float, required=True); eval_parser.add_argument("--under-routing-score", type=float, required=True); eval_parser.add_argument("--sequence-score", type=float, required=True); eval_parser.add_argument("--source-ref")
    compare = sub.add_parser("compare-releases"); compare.add_argument("--telemetry-db", type=Path, default=DEFAULT_TELEMETRY_DB)
    export = sub.add_parser("export"); export.add_argument("--telemetry-db", type=Path, default=DEFAULT_TELEMETRY_DB); export.add_argument("--format", choices=("json", "csv"), required=True); export.add_argument("--output", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    handlers = {"reasoning-decide": reasoning_decide, "init": initialize, "transition": transition, "invocation-start": invocation_start, "invocation-finish": invocation_finish, "evaluate": evaluate_attempt, "record": record, "finding": finding, "route": route, "decision": decision, "handoff": create_handoff, "validate-handoff": validate_handoff, "technical-handoff": create_technical_handoff, "technical-handoff-get": get_technical_handoff, "teachback-evaluate": evaluate_teachback, "context-pack": context_pack, "discovery": discovery_record, "summary": summary, "dashboard": dashboard, "report-cost": report_cost, "eval-result": release_eval, "compare-releases": compare_releases, "export": export_telemetry}
    try: result = handlers[args.command](args)
    except (RuntimeErrorSafe, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr); return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
