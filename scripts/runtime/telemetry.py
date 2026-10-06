"""Resolução independente dos destinos de telemetria do Runtime V3."""
from pathlib import Path
from typing import Any
import sqlite3

def telemetry_db_for_state(state: dict[str, Any], root: Path) -> Path:
    return Path(state.get("telemetry_db", root.parent / ".telemetry/jarvis.db")).resolve()

def open_connection(path: Path, ddl: str) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(ddl)
    return connection

def sync_run(connection: sqlite3.Connection, state: dict[str, Any]) -> None:
    metrics, budget, routing = state["metrics"], state["budget"], state["routing"]
    boolean = lambda value: None if value is None else int(value)
    values = (state["run_id"], state["task_id"], state["started_at"], state["finished_at"], metrics["duration_ms"], state["current_state"], state["complexity"], state["risk_class"], state["operational_mode"], state["reasoning_class"], state["jarvis_version"], state["policy_version"], state["contracts_version"], state["config_hash"], budget["budget_limit"], budget["budget_used"], int(budget["budget_override"]), budget["budget_override_reason"], metrics["agent_invocation_count"], len(state["agents_used"]), metrics["rework_cycles"], metrics["stop_count"], boolean(metrics["first_pass_success"]), boolean(metrics["human_gate_pass_on_first_attempt"]), routing["routing_outcome"], metrics["input_tokens"], metrics["cached_input_tokens"], metrics["output_tokens"], metrics["credits"])
    connection.execute("INSERT INTO runs(run_id,task_id,started_at,finished_at,duration_ms,status,complexity,risk_class,operational_mode,reasoning_class,jarvis_version,policy_version,contracts_version,config_hash,budget_limit,budget_used,budget_override,budget_override_reason,agent_invocation_count,unique_agent_count,rework_cycles,stop_count,first_pass_success,human_gate_pass_on_first_attempt,routing_outcome,input_tokens,cached_input_tokens,output_tokens,credits) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET finished_at=excluded.finished_at,duration_ms=excluded.duration_ms,status=excluded.status,reasoning_class=excluded.reasoning_class,budget_used=excluded.budget_used,budget_override=excluded.budget_override,budget_override_reason=excluded.budget_override_reason,agent_invocation_count=excluded.agent_invocation_count,unique_agent_count=excluded.unique_agent_count,rework_cycles=excluded.rework_cycles,stop_count=excluded.stop_count,first_pass_success=excluded.first_pass_success,human_gate_pass_on_first_attempt=excluded.human_gate_pass_on_first_attempt,routing_outcome=excluded.routing_outcome,input_tokens=excluded.input_tokens,cached_input_tokens=excluded.cached_input_tokens,output_tokens=excluded.output_tokens,credits=excluded.credits", values)

def ensure_migrations(connection: sqlite3.Connection) -> None:
    for table in ("agent_invocations", "execution_attempts"):
        existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column in ("model_requested", "model_effective", "context_budget", "progress_event", "reasoning_effort_effective"):
            if column not in existing: connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
    migrations = {"agent_invocations": {"team": "TEXT"}, "rag_queries": {"team": "TEXT"}, "technical_handoffs": {"teachback_required": "INTEGER NOT NULL DEFAULT 0", "teachback_questions": "INTEGER NOT NULL DEFAULT 0"}, "teachback_evaluations": {"developer_requested_deeper_explanation": "INTEGER NOT NULL DEFAULT 0"}}
    for table, columns in migrations.items():
        existing = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        for column, definition in columns.items():
            if column not in existing: connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

__all__ = ["ensure_migrations", "open_connection", "sync_run", "telemetry_db_for_state"]
