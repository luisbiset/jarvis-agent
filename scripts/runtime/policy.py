"""Policy V3 isolada do adaptador de compatibilidade do Runtime."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "contracts" / "reasoning-policy.json"


def load_reasoning_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def reasoning_decision(signals: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_reasoning_policy()
    limits, weights = policy["limits"], policy["weights"]
    ambiguity, complexity = signals["ambiguity_score"], signals["complexity_score"]
    if not 0 <= ambiguity <= limits["max_ambiguity_points"]: raise ValueError("ambiguity_score fora dos limites")
    if not 0 <= complexity <= limits["max_complexity_points"]: raise ValueError("complexity_score fora dos limites")
    if signals["estimated_files"] < 0 or signals["estimated_modules"] < 0: raise ValueError("estimativas não podem ser negativas")
    contributions = {
        "architectural": weights["architectural"] if signals["architectural"] else 0,
        "production_critical": weights["production_critical"] if signals["production_critical"] else 0,
        "security_sensitive": weights["security_sensitive"] if signals["security_sensitive"] else 0,
        "database_migration": weights["database_migration"] if signals["database_migration"] else 0,
        "multiple_modules": weights["multiple_modules"] if signals["estimated_modules"] >= limits["multiple_modules_min"] else 0,
        "many_files": weights["many_files"] if signals["estimated_files"] >= limits["many_files_min"] else 0,
        "tests_required": weights["tests_required"] if signals["tests_required"] else 0,
        "ambiguity": ambiguity, "complexity": complexity,
    }
    score = sum(contributions.values()); thresholds = policy["thresholds"]
    no_detail = not any((signals["estimated_files"], signals["estimated_modules"], signals["architectural"], signals["production_critical"], signals["database_migration"], signals["security_sensitive"], signals["tests_required"], ambiguity, complexity))
    incomplete = no_detail and (signals["task_type"] == "GENERAL" or signals["task_type"] in {"BACKEND", "FRONTEND", "DATABASE", "TEST", "SECURITY", "ARCHITECTURE", "INTEGRATION"})
    level = policy["default_level"] if incomplete else "INSTANT" if score <= thresholds["instant_max_score"] else "MEDIUM" if score <= thresholds["medium_max_score"] else "HIGH"
    config = policy["levels"][level]
    return {"policy_version": policy["policy_version"], "level": level, "reasoning_class": config["reasoning_class"], "reasoning_effort": config["reasoning_effort"], "model": config["model"], "context_budget": config["context_budget"], "max_input_tokens": config["max_input_tokens"], "score": score, "contributions": contributions, "max_attempts": policy["budget"]["max_attempts"], "max_child_depth": policy["budget"]["max_child_depth"], "max_model_calls": policy["budget"]["hard_max_model_calls"], "max_duration_ms": policy["budget"]["max_duration_ms"], "escalation_allowed": bool(policy["escalation"]["enabled"] and level == policy["escalation"]["allowed_from"]), "max_escalations": policy["escalation"]["max_per_task"], "reason": "incomplete signals: default MEDIUM" if incomplete else f"score {score:g}: {level}", "signals": signals}


def invocation_policy(state: dict[str, Any], agent: str, task_type: str | None = None) -> dict[str, Any]:
    policy = load_reasoning_policy(); requested = state["reasoning"]["current_level"]; normalized = agent.lower(); task = (task_type or state["reasoning"]["signals"].get("task_type", "GENERAL")).upper()
    category = "router" if "router" in normalized else "test" if "test" in normalized or task == "TEST" else "documentation" if task in {"DOCUMENTATION", "EXPLANATION"} else "default"
    cap = policy["agent_caps"][category]; order = {level: index for index, level in enumerate(("INSTANT", "MEDIUM", "HIGH"))}; effective = requested if order[requested] <= order[cap] else cap; config = policy["levels"][effective]
    return {"level": effective, "model": config["model"], "reasoning_effort": config["reasoning_effort"], "context_budget": config["context_budget"], "cap": cap, "category": category}

__all__ = ["invocation_policy", "load_reasoning_policy", "reasoning_decision"]
