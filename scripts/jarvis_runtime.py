#!/usr/bin/env python3
"""Runtime local do Jarvis V2: estado, handoff, provenance e telemetria segura."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "contracts/version.json"
DEFAULT_RUNS_DIR = ROOT / ".jarvis/runs"

COMPLEXITIES = ("TRIVIAL", "LOCALIZED", "TRANSVERSAL", "CRITICAL")
RISKS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
MODES = ("COPILOT", "ASSISTED_AUTOPILOT", "READ_ONLY_AUDIT")
REASONING = ("FAST", "NORMAL", "DEEP")
STATES = (
    "NEW",
    "DISCOVERY",
    "PLAN_READY",
    "PLAN_APPROVED",
    "IMPLEMENTING",
    "VALIDATING",
    "REVIEW_READY",
    "HUMAN_GATE",
    "HOMOLOGATION_READY",
    "DONE",
    "BLOCKED",
)
STOP_REASONS = (
    "AMBIGUOUS_REQUIREMENT",
    "SHARED_CONTRACT_OUT_OF_SCOPE",
    "TEST_CONTRADICTION",
    "EXTERNAL_AUTHORIZATION_REQUIRED",
    "INSUFFICIENT_CONTEXT",
    "VALIDATION_NOT_REPRODUCIBLE",
    "SPECIALIST_DIVERGENCE",
    "NEEDS_EXPLANATION",
)

BUDGETS = {
    "TRIVIAL": {"max_agents": 2, "max_parallel_agents": 1},
    "LOCALIZED": {"max_agents": 3, "max_parallel_agents": 2},
    "TRANSVERSAL": {"max_agents": 6, "max_parallel_agents": 2},
    "CRITICAL": {"max_agents": 8, "max_parallel_agents": 2},
}
REQUIRED_REVIEWERS = {
    "LOW": [],
    "MEDIUM": ["technical_qa_or_diff_auditor"],
    "HIGH": ["technical_qa", "diff_auditor", "system_reviewer"],
    "CRITICAL": ["technical_qa", "diff_auditor", "system_reviewer", "human_explainability_gate"],
}
TRANSITIONS = {
    "NEW": {"DISCOVERY", "PLAN_APPROVED", "BLOCKED"},
    "DISCOVERY": {"PLAN_READY", "BLOCKED"},
    "PLAN_READY": {"PLAN_APPROVED", "DISCOVERY", "BLOCKED"},
    "PLAN_APPROVED": {"IMPLEMENTING", "VALIDATING", "BLOCKED"},
    "IMPLEMENTING": {"VALIDATING", "BLOCKED"},
    "VALIDATING": {"REVIEW_READY", "IMPLEMENTING", "BLOCKED"},
    "REVIEW_READY": {"HUMAN_GATE", "IMPLEMENTING", "BLOCKED"},
    "HUMAN_GATE": {"HOMOLOGATION_READY", "DONE", "IMPLEMENTING", "BLOCKED"},
    "HOMOLOGATION_READY": {"DONE", "IMPLEMENTING", "BLOCKED"},
    "DONE": set(),
    "BLOCKED": {"DISCOVERY", "PLAN_READY", "PLAN_APPROVED", "IMPLEMENTING", "VALIDATING"},
}

SENSITIVE_KEY = re.compile(r"(?i)(api.?key|password|passwd|secret|credential|authorization|cookie|patient|paciente)")
SENSITIVE_VALUE = re.compile(r"(?i)(bearer\s+[a-z0-9._-]+|https?://[^\s]*(?:intra|saude|local)[^\s]*|api[_-]?key\s*[=:])")
SAFE_RECORD_FIELDS = {
    "stage",
    "agent",
    "status",
    "reasoning_class",
    "started_at",
    "finished_at",
    "input_refs",
    "output_artifact",
    "files_read",
    "files_changed",
    "validations",
    "duration_ms",
    "token_or_credit_cost",
    "retry_count",
    "blocker",
    "budget_justification",
}


class RuntimeErrorSafe(RuntimeError):
    """Erro operacional apresentado sem stack trace por padrão."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeErrorSafe(f"JSON inválido ou inacessível em {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeErrorSafe(f"objeto JSON esperado em {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def jarvis_version() -> dict[str, Any]:
    return load_json(VERSION_PATH)


def make_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"jarvis-{stamp}-{secrets.token_hex(4)}"


def run_path(value: str | Path) -> Path:
    path = Path(value).resolve()
    if not (path / "state.json").is_file():
        raise RuntimeErrorSafe(f"execução inválida: state.json ausente em {path}")
    return path


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


def initial_state(
    task_id: str,
    complexity: str,
    risk_class: str,
    operational_mode: str,
    reasoning_class: str,
    budget_justification: str | None,
) -> dict[str, Any]:
    budget = dict(BUDGETS[complexity])
    budget.update(
        {
            "required_reviewers": REQUIRED_REVIEWERS[risk_class],
            "override_justification": budget_justification,
        }
    )
    timestamp = now()
    return {
        "schema_version": "2.0.0",
        "run_id": make_run_id(),
        "task_id": task_id,
        "jarvis_version": jarvis_version()["jarvis_version"],
        "created_at": timestamp,
        "updated_at": timestamp,
        "current_state": "NEW",
        "complexity": complexity,
        "risk_class": risk_class,
        "operational_mode": operational_mode,
        "reasoning_class": reasoning_class,
        "budget": budget,
        "history": [{"from": None, "to": "NEW", "at": timestamp, "reason": "run initialized"}],
        "agents_used": [],
        "metrics": {"duration_ms": 0, "token_or_credit_cost": 0, "retry_count": 0},
        "gate_decision": None,
    }


def initialize(args: argparse.Namespace) -> dict[str, Any]:
    if args.complexity in {"TRANSVERSAL", "CRITICAL"} and args.reasoning_class == "FAST":
        raise RuntimeErrorSafe("TRANSVERSAL/CRITICAL não pode iniciar em FAST; use NORMAL ou DEEP")
    state = initial_state(
        args.task_id,
        args.complexity,
        args.risk_class,
        args.operational_mode,
        args.reasoning_class,
        args.budget_justification,
    )
    root = Path(args.runs_dir).resolve() / state["run_id"]
    root.mkdir(parents=True, exist_ok=False)
    (root / "context-packs").mkdir()
    write_json(root / "state.json", state)
    append_jsonl(
        root / "events.jsonl",
        {"event": "RUN_INITIALIZED", "at": state["created_at"], "run_id": state["run_id"], "state": "NEW"},
    )
    return {"run_dir": str(root), "state": state}


def transition(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    source = state["current_state"]
    target = args.to
    if target not in TRANSITIONS.get(source, set()):
        raise RuntimeErrorSafe(f"transição não permitida: {source} -> {target}")
    if source == "NEW" and target == "PLAN_APPROVED" and state["complexity"] not in {"TRIVIAL", "LOCALIZED"}:
        raise RuntimeErrorSafe("somente tarefas TRIVIAL/LOCALIZED podem usar aprovação implícita do pedido direto")
    if state["operational_mode"] == "READ_ONLY_AUDIT" and target == "IMPLEMENTING":
        raise RuntimeErrorSafe("READ_ONLY_AUDIT não permite transição para IMPLEMENTING")
    if target == "BLOCKED" and not args.stop_reason:
        raise RuntimeErrorSafe("transição para BLOCKED exige --stop-reason")
    if target != "BLOCKED" and args.stop_reason:
        raise RuntimeErrorSafe("--stop-reason é exclusivo da transição para BLOCKED")
    timestamp = now()
    entry = {"from": source, "to": target, "at": timestamp, "reason": args.reason, "stop_reason": args.stop_reason}
    state["current_state"] = target
    state["updated_at"] = timestamp
    state["history"].append(entry)
    if args.gate_decision:
        if source != "HUMAN_GATE":
            raise RuntimeErrorSafe("--gate-decision só pode ser registrado a partir de HUMAN_GATE")
        state["gate_decision"] = args.gate_decision
    write_json(root / "state.json", state)
    append_jsonl(root / "events.jsonl", {"event": "STATE_TRANSITION", "run_id": state["run_id"], **entry})
    return state


def record(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    if (args.duration_ms or 0) < 0 or (args.token_or_credit_cost or 0) < 0 or (args.retry_count or 0) < 0:
        raise RuntimeErrorSafe("duração, custo e retry_count não podem ser negativos")
    record_data = {key: value for key, value in vars(args).items() if key in SAFE_RECORD_FIELDS and value not in (None, [])}
    assert_safe_metadata(record_data)
    agent = record_data.get("agent")
    if agent and agent not in state["agents_used"]:
        projected = len(state["agents_used"]) + 1
        if projected > state["budget"]["max_agents"] and not args.budget_justification:
            raise RuntimeErrorSafe(
                f"budget excedido: {projected} agentes para máximo {state['budget']['max_agents']}; informe --budget-justification"
            )
        state["agents_used"].append(agent)
        state["agents_used"].sort()
        if projected > state["budget"]["max_agents"]:
            state["budget"]["override_justification"] = args.budget_justification
    state["metrics"]["duration_ms"] += args.duration_ms or 0
    state["metrics"]["token_or_credit_cost"] += args.token_or_credit_cost or 0
    state["metrics"]["retry_count"] += args.retry_count or 0
    state["updated_at"] = now()
    event = {"event": "STAGE_RECORDED", "at": state["updated_at"], "run_id": state["run_id"], **record_data}
    append_jsonl(root / "events.jsonl", event)
    write_json(root / "state.json", state)
    return event


def handoff_template(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "run_id": state["run_id"],
        "jarvis_version": state["jarvis_version"],
        "status": "IN_PROGRESS",
        "stage": state["current_state"],
        "complexity": state["complexity"],
        "risk_class": state["risk_class"],
        "operational_mode": state["operational_mode"],
        "reasoning_class": state["reasoning_class"],
        "requirement_ids": [],
        "files": [],
        "contracts_changed": [],
        "decisions": [],
        "validations": {"executed": [], "passed": [], "failed": [], "not_executed": []},
        "risks": [],
        "limitations": [],
        "blockers": [],
        "stop_reason": None,
        "ownership": {},
        "next": [],
    }


def create_handoff(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    handoff = handoff_template(state)
    destination = Path(args.output).resolve() if args.output else root / f"handoff-{state['current_state'].lower()}.json"
    write_json(destination, handoff)
    return {"handoff": str(destination)}


def validate_handoff_data(data: dict[str, Any]) -> list[str]:
    schema = load_json(ROOT / "contracts/handoff.schema.json")
    errors: list[str] = []
    required = set(schema["required"])
    missing = required - set(data)
    extra = set(data) - set(schema["properties"])
    if missing:
        errors.append(f"campos ausentes: {sorted(missing)}")
    if extra:
        errors.append(f"campos não permitidos: {sorted(extra)}")
    enum_fields = ("status", "stage", "complexity", "risk_class", "operational_mode", "reasoning_class", "stop_reason")
    for field in enum_fields:
        if field in data and data[field] not in schema["properties"][field]["enum"]:
            errors.append(f"{field} inválido: {data[field]!r}")
    if data.get("schema_version") != "2.0.0":
        errors.append("schema_version deve ser 2.0.0")
    requirements = data.get("requirement_ids", [])
    for index, file_entry in enumerate(data.get("files", [])):
        if not isinstance(file_entry, dict):
            errors.append(f"files[{index}] não é objeto")
            continue
        for field in ("path", "purpose", "requirement_ids", "owner"):
            if not file_entry.get(field):
                errors.append(f"files[{index}] sem {field}")
        unknown = set(file_entry.get("requirement_ids", [])) - set(requirements)
        if unknown:
            errors.append(f"files[{index}] referencia requisitos ausentes do handoff: {sorted(unknown)}")
    validations = data.get("validations", {})
    if not isinstance(validations, dict) or set(validations) != {"executed", "passed", "failed", "not_executed"}:
        errors.append("validations deve declarar executed, passed, failed e not_executed")
    if data.get("status") in {"BLOCKED", "NEEDS_EXPLANATION"} and not data.get("stop_reason"):
        errors.append("status bloqueante exige stop_reason")
    if data.get("risk_class") in {"HIGH", "CRITICAL"} and data.get("status") in {"READY_FOR_REVIEW", "DONE"}:
        if not data.get("decisions"):
            errors.append("handoff HIGH/CRITICAL pronto exige provenance em decisions")
    try:
        assert_safe_metadata(data)
    except RuntimeErrorSafe as exc:
        errors.append(str(exc))
    return errors


def validate_handoff(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.path).resolve()
    errors = validate_handoff_data(load_json(path))
    if errors:
        raise RuntimeErrorSafe("handoff inválido: " + "; ".join(errors))
    return {"valid": True, "path": str(path)}


def context_pack(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    refs = sorted(set(args.ref))
    assert_safe_metadata(refs, "evidence_refs")
    payload = {
        "schema_version": 1,
        "run_id": state["run_id"],
        "kind": args.kind,
        "created_at": now(),
        "baseline": args.baseline,
        "evidence_refs": refs,
        "content_policy": "references_and_hashes_only",
    }
    destination = root / "context-packs" / f"{args.kind}.json"
    write_json(destination, payload)
    return {"context_pack": str(destination), "refs": len(refs)}


def discovery_record(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    refs = sorted(set(args.ref))
    assert_safe_metadata(refs, "evidence_refs")
    query_hash = hashlib.sha256(args.query.encode("utf-8")).hexdigest()
    event = {
        "schema_version": 1,
        "run_id": state["run_id"],
        "at": now(),
        "baseline": args.baseline,
        "query_hash": query_hash,
        "evidence_refs": refs,
        "note": "facts_only_not_conclusions",
    }
    append_jsonl(root / "discovery-cache.jsonl", event)
    return {"query_hash": query_hash, "refs": len(refs)}


def summary(args: argparse.Namespace) -> dict[str, Any]:
    root = run_path(args.run_dir)
    state = load_json(root / "state.json")
    return {
        "run_id": state["run_id"],
        "jarvis_version": state["jarvis_version"],
        "task_id": state["task_id"],
        "state": state["current_state"],
        "complexity": state["complexity"],
        "risk_class": state["risk_class"],
        "operational_mode": state["operational_mode"],
        "reasoning_class": state["reasoning_class"],
        "agents": state["agents_used"],
        "agent_count": len(state["agents_used"]),
        "budget": state["budget"],
        "metrics": state["metrics"],
        "gate_decision": state["gate_decision"],
    }


def dashboard(args: argparse.Namespace) -> dict[str, Any]:
    runs_dir = Path(args.runs_dir).resolve()
    states = []
    if runs_dir.is_dir():
        for path in sorted(runs_dir.glob("*/state.json")):
            try:
                states.append(load_json(path))
            except RuntimeErrorSafe:
                continue
    total_cost = sum(item.get("metrics", {}).get("token_or_credit_cost", 0) for item in states)
    total_duration = sum(item.get("metrics", {}).get("duration_ms", 0) for item in states)
    total_retries = sum(item.get("metrics", {}).get("retry_count", 0) for item in states)
    over_budget = sum(len(item.get("agents_used", [])) > item.get("budget", {}).get("max_agents", 0) for item in states)
    return {
        "runs": len(states),
        "total_token_or_credit_cost": total_cost,
        "total_duration_ms": total_duration,
        "total_retries": total_retries,
        "over_budget_runs": over_budget,
        "human_gate_decisions": {
            decision: sum(item.get("gate_decision") == decision for item in states)
            for decision in ("APPROVED", "CHANGES_REQUESTED", "REJECTED")
        },
        "by_complexity": {
            complexity: sum(item.get("complexity") == complexity for item in states) for complexity in COMPLEXITIES
        },
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Inicializa uma execução local.")
    init.add_argument("--task-id", required=True)
    init.add_argument("--complexity", choices=COMPLEXITIES, required=True)
    init.add_argument("--risk-class", choices=RISKS, required=True)
    init.add_argument("--operational-mode", choices=MODES, required=True)
    init.add_argument("--reasoning-class", choices=REASONING, required=True)
    init.add_argument("--budget-justification")
    init.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)

    move = sub.add_parser("transition", help="Aplica uma transição permitida.")
    move.add_argument("--run-dir", required=True)
    move.add_argument("--to", choices=STATES, required=True)
    move.add_argument("--reason", required=True)
    move.add_argument("--stop-reason", choices=STOP_REASONS)
    move.add_argument("--gate-decision", choices=("APPROVED", "CHANGES_REQUESTED", "REJECTED"))

    item = sub.add_parser("record", help="Registra evento de estágio sem conteúdo sensível.")
    item.add_argument("--run-dir", required=True)
    item.add_argument("--stage", choices=STATES, required=True)
    item.add_argument("--agent")
    item.add_argument("--status", required=True)
    item.add_argument("--reasoning-class", choices=REASONING)
    item.add_argument("--started-at")
    item.add_argument("--finished-at")
    item.add_argument("--input-ref", action="append", dest="input_refs", default=[])
    item.add_argument("--output-artifact")
    item.add_argument("--file-read", action="append", dest="files_read", default=[])
    item.add_argument("--file-changed", action="append", dest="files_changed", default=[])
    item.add_argument("--validation", action="append", dest="validations", default=[])
    item.add_argument("--duration-ms", type=int, default=0)
    item.add_argument("--token-or-credit-cost", type=float, default=0)
    item.add_argument("--retry-count", type=int, default=0)
    item.add_argument("--blocker")
    item.add_argument("--budget-justification")

    handoff = sub.add_parser("handoff", help="Cria um handoff preenchível a partir do estado.")
    handoff.add_argument("--run-dir", required=True)
    handoff.add_argument("--output")

    handoff_validation = sub.add_parser("validate-handoff", help="Valida o contrato mínimo de handoff.")
    handoff_validation.add_argument("path")

    pack = sub.add_parser("context-pack", help="Cria pacote de contexto baseado em referências.")
    pack.add_argument("--run-dir", required=True)
    pack.add_argument("--kind", choices=("requirement", "database", "contract", "git-baseline"), required=True)
    pack.add_argument("--baseline", required=True)
    pack.add_argument("--ref", action="append", required=True)

    discovery = sub.add_parser("discovery", help="Registra cache de fatos por hash da busca.")
    discovery.add_argument("--run-dir", required=True)
    discovery.add_argument("--baseline", required=True)
    discovery.add_argument("--query", required=True)
    discovery.add_argument("--ref", action="append", required=True)

    run_summary = sub.add_parser("summary", help="Resume custo, duração, agentes, retries e gate.")
    run_summary.add_argument("--run-dir", required=True)

    metrics = sub.add_parser("dashboard", help="Agrega métricas locais de execuções.")
    metrics.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    return root


def main() -> int:
    args = parser().parse_args()
    handlers = {
        "init": initialize,
        "transition": transition,
        "record": record,
        "handoff": create_handoff,
        "validate-handoff": validate_handoff,
        "context-pack": context_pack,
        "discovery": discovery_record,
        "summary": summary,
        "dashboard": dashboard,
    }
    try:
        result = handlers[args.command](args)
    except (RuntimeErrorSafe, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
