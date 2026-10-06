"""Planejamento mínimo e determinístico do fluxo AGHUse.

Este módulo não chama agentes nem serviços externos. Ele somente transforma
sinais já resolvidos pela policy em uma estratégia auditável.
"""
from __future__ import annotations

from typing import Any


def _specialist(task_type: str, signals: dict[str, Any]) -> str:
    mapping = {
        "DATABASE": "aghuse_banco",
        "TEST": "aghuse_testes",
        "FRONTEND": "aghuse_frontend",
        "SECURITY": "aghuse_seguranca",
        "BACKEND": "aghuse_backend",
    }
    if task_type in mapping:
        return mapping[task_type]
    if signals.get("database"):
        return "aghuse_banco"
    if signals.get("security"):
        return "aghuse_seguranca"
    return "aghuse_backend"


def plan_execution(signals: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retorna o menor plano compatível com os sinais da tarefa."""
    policy = policy or {}
    complexity = str(signals.get("complexity", "LOCALIZED")).upper()
    risk = str(signals.get("risk_class", "MEDIUM")).upper()
    task_type = str(signals.get("task_type", "BACKEND")).upper()
    contract_changed = bool(signals.get("contract_changed"))
    tests_changed = bool(signals.get("tests_changed"))
    review_required = risk in {"HIGH", "CRITICAL"} or contract_changed or tests_changed
    specialist = _specialist(task_type, signals)

    if complexity == "TRIVIAL":
        agents = [specialist]
        teams = ["DESENVOLVIMENTO"]
        strategy, retry, cost, context = "MINIMAL_FIRST", "NONE", "LOW", "SMALL"
        review_required = False
    elif complexity == "LOCALIZED":
        agents = [specialist]
        teams = ["DESENVOLVIMENTO"]
        strategy, retry, cost, context = "MINIMAL_FIRST", "TARGETED", "LOW", "SMALL"
    elif complexity == "TRANSVERSAL":
        agents = ["aghuse_analise", specialist, "aghuse_qualidade"]
        teams = ["ANALISE", "DESENVOLVIMENTO", "REVISAO_QUALIDADE"]
        strategy, retry, cost, context = "MINIMAL_FIRST", "ONE_ESCALATION", "MEDIUM", "MEDIUM"
        review_required = True
    else:
        agents = ["aghuse_analise", specialist, "aghuse_qualidade", "aghuse_revisor"]
        teams = ["ANALISE", "DESENVOLVIMENTO", "REVISAO_QUALIDADE"]
        strategy, retry, cost, context = "FIXED_CRITICAL", "ONE_ESCALATION", "HIGH", "LARGE"
        review_required = True

    if signals.get("escalated"):
        strategy = "ESCALATED"
    max_calls = int(policy.get("max_model_calls", max(1, len(agents))))
    return {
        "strategy": strategy,
        "agents_planned": agents,
        "teams_planned": teams,
        "max_parallel_agents": 1 if complexity in {"TRIVIAL", "LOCALIZED"} else min(2, len(agents)),
        "max_model_calls": min(max_calls, max(1, len(agents))),
        "context_budget": context,
        "review_required": review_required,
        "retry_policy": retry,
        "estimated_cost_class": cost,
        "rag_available": bool(signals.get("rag_available", False)),
        "planner_version": "1.0.0",
    }


def compare_strategies(current: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    """Compara decisões sem executar a estratégia alternativa."""
    current_agents = current.get("agents_planned")
    current_calls = current.get("max_model_calls")
    if current_calls is None and current_agents:
        current_calls = len(current_agents)
    optimized_calls = int(optimized.get("max_model_calls", len(optimized.get("agents_planned", []))))
    saved = max(0, int(current_calls) - optimized_calls) if current_calls is not None else None
    percent = round(saved / int(current_calls) * 100, 2) if current_calls else None
    return {
        "baseline_strategy": current,
        "optimized_strategy": optimized,
        "baseline_estimated_calls": current_calls if current_calls is not None else "UNKNOWN/NOT_OBSERVED",
        "optimized_estimated_calls": optimized_calls,
        "estimated_calls_saved": saved if saved is not None else "UNKNOWN/NOT_OBSERVED",
        "estimated_calls_saved_percent": percent if percent is not None else "UNKNOWN/NOT_OBSERVED",
        "quality_delta": "UNKNOWN/NOT_OBSERVED",
        "routing_delta": "UNKNOWN/NOT_OBSERVED",
        "alternative_executed": False,
    }
