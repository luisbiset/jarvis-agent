"""Contrato e apresentação segura das métricas exibidas no chat."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
UNKNOWN = "UNKNOWN/NOT_OBSERVED"


def _value(value: Any, fallback: str = UNKNOWN) -> Any:
    return fallback if value is None or value == "" else value


def _text(value: Any) -> str:
    return str(_value(value))


def policy_decision(*, technical: bool = True) -> dict[str, Any]:
    """Resolve apenas valores decididos pela policy, sem inventar consumo."""
    path = Path(__file__).resolve().parents[1] / "contracts" / "reasoning-policy.json"
    policy = json.loads(path.read_text(encoding="utf-8"))
    level = "MEDIUM" if technical else "INSTANT"
    selected = policy["levels"][level]
    return {"complexity": "LOCALIZED" if technical else "TRIVIAL", "risk_class": "MEDIUM" if technical else "LOW", "operational_mode": "COPILOT", "model": selected["model"], "reasoning_effort": selected["reasoning_effort"], "max_attempts": policy["budget"]["max_attempts"], "max_agents": 2 if technical else 1}


def initial(message: str, *, rag: dict[str, Any], decision: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = decision or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": "INITIAL",
        "complexity": _value(decision.get("complexity")),
        "risk_class": _value(decision.get("risk_class")),
        "operational_mode": _value(decision.get("operational_mode")),
        "model": _value(decision.get("model")),
        "reasoning": _value(decision.get("reasoning_effort")),
        "attempts_used": 0,
        "attempts_budget": _value(decision.get("max_attempts")),
        "agents_used": 0,
        "agents_budget": _value(decision.get("max_agents")),
        "duration_ms": UNKNOWN,
        "credits": UNKNOWN,
        "credits_status": "UNKNOWN/NOT_OBSERVED",
        "termination_reason": "PLANNING",
        "data_quality": "POLICY_DECIDED",
        "message_hash": hashlib.sha256(message.encode()).hexdigest(),
        "rag": rag_metrics(rag),
    }


def final(initial_metrics: dict[str, Any], *, reason: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or {}
    metrics = state.get("metrics", {})
    budget = state.get("budget", {})
    reasoning = state.get("reasoning", {})
    credits = metrics.get("credits")
    duration = metrics.get("duration_ms")
    return {
        **initial_metrics,
        "phase": "FINAL",
        "attempts_used": _value(metrics.get("retry_count"), 0) + 1 if state else UNKNOWN,
        "attempts_budget": _value(budget.get("max_model_calls"), initial_metrics.get("attempts_budget", UNKNOWN)),
        "agents_used": _value(metrics.get("agent_invocation_count"), UNKNOWN),
        "agents_budget": _value(budget.get("max_agents"), initial_metrics.get("agents_budget", UNKNOWN)),
        "duration_ms": _value(duration),
        "credits": _value(credits),
        "credits_status": "OBSERVED" if credits is not None else "UNKNOWN/NOT_OBSERVED",
        "reasoning": f"{_text(initial_metrics.get('reasoning'))}->{_text(reasoning.get('effective_reasoning') or reasoning.get('current_level'))}",
        "termination_reason": reason,
        "data_quality": "OBSERVED" if state else "NOT_EXECUTED",
    }


def rag_metrics(rag: dict[str, Any] | None) -> dict[str, Any]:
    rag = rag or {}
    reason = rag.get("reason")
    if rag.get("bypassed"):
        mode, quality = "NOT_USED", "RAG_BYPASS_AUTHORIZED"
    elif reason == "rag_index_not_found":
        mode, quality = "NOT_USED", "RAG_BLOCKED"
    elif rag.get("retrieved"):
        mode, quality = rag.get("retrieval_mode", UNKNOWN), "OBSERVED"
    else:
        mode, quality = "NOT_USED", "NOT_REQUIRED"
    return {
        "mode": mode,
        "required": bool(rag.get("required", False)),
        "selected_chunks": rag.get("selected_chunks", len(rag.get("hits", []))) if rag.get("retrieved") else UNKNOWN,
        "cache_hit": rag.get("cache_hit", UNKNOWN),
        "data_quality": quality,
    }


def human(metrics: dict[str, Any]) -> str:
    if metrics.get("phase") == "INITIAL":
        return "Métricas iniciais: " + " | ".join((
            f"complexidade {metrics['complexity']}", f"risco {metrics['risk_class']}",
            f"modo {metrics['operational_mode']}", f"modelo LLM {metrics['model']}",
            f"reasoning {metrics['reasoning']}", f"tentativas {metrics['attempts_used']}/{metrics['attempts_budget']}",
            f"agentes planejados {metrics['agents_used']}/{metrics['agents_budget']}", f"créditos {metrics['credits']}",
        ))
    return "Métricas finais: " + " | ".join((
        f"estado {metrics['termination_reason']}", f"duração {metrics['duration_ms']}",
        f"tentativas {metrics['attempts_used']}/{metrics['attempts_budget']}",
        f"agentes {metrics['agents_used']}/{metrics['agents_budget']}",
        f"reasoning {metrics['reasoning']}", f"créditos {metrics['credits']}", f"término {metrics['termination_reason']}",
    ))


def json_block(metrics: dict[str, Any]) -> str:
    return json.dumps({"metrics": metrics}, ensure_ascii=False, sort_keys=True)
