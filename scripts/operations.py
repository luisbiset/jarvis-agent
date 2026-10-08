"""Catálogo e propostas seguras de operações do Workspace."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aghuse_assistant.agents import allowed_agents

def skill_config(skill: str) -> dict[str, Any]:
    operation = {"analisar": "ANALYZE", "planejar": "PLAN", "implementar": "IMPLEMENT", "validar": "VALIDATE", "manutencao": "MANUTENCAO"}[skill]
    return {"allowed_agents": allowed_agents(operation), "requires_checkpoint": operation == "MANUTENCAO", "human_gate": operation == "MANUTENCAO"}

OPERATION_SKILLS = {"ANALYZE": "analisar", "PLAN": "planejar", "IMPLEMENT": "implementar", "VALIDATE": "validar", "MANUTENCAO": "manutencao"}

OPERATIONS = {
    "MANUTENCAO": {"name": "Manutencao", "description": "Manter o proprio AGHUse Assistant: codigo, skills, plugins, contratos, agentes, testes e documentacao.", "mutates": True, "output": "maintenance", "required": ["objective"]},
    "ANALYZE": {"name": "Analisar", "description": "Investigar perguntas verificáveis, rastrear fluxos e produzir impacto com evidências e limitações.", "mutates": False, "output": "analysis", "required": ["objective"]},
    "PLAN": {"name": "Planejar", "description": "Criar plano técnico com escopo, agents, budget e critérios.", "mutates": False, "output": "plan", "required": ["objective"]},
    "IMPLEMENT": {"name": "Implementar", "description": "Preparar implementação controlada com diff e testes.", "mutates": True, "output": "implementation", "required": ["objective", "acceptance_criteria"]},
    "VALIDATE": {"name": "Validar", "description": "Executar validações e diagnosticar regressões sem corrigir automaticamente.", "mutates": False, "output": "validation", "required": ["objective"]},
}


def catalog() -> list[dict[str, Any]]:
    return [{"operation_id": key, "template_version": "2.0.0", "skill": OPERATION_SKILLS[key], "skill_policy": skill_config(OPERATION_SKILLS[key]), **value} for key, value in OPERATIONS.items()]


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def validate(operation_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
    operation = OPERATIONS.get(operation_id.upper())
    if not operation:
        raise ValueError("operação inválida")
    clean = {key: " ".join(str(value).split())[:4000] for key, value in parameters.items() if value is not None and str(value).strip()}
    missing = [key for key in operation["required"] if not clean.get(key)]
    if missing:
        raise ValueError("parâmetros obrigatórios ausentes: " + ", ".join(missing))
    return clean


def create_preview(operation_id: str, project_id: str, parameters: dict[str, Any], *, rag: dict[str, Any], metrics: dict[str, Any], provider: str) -> dict[str, Any]:
    operation_id = operation_id.upper()
    clean = validate(operation_id, parameters)
    operation = OPERATIONS[operation_id]
    proposal_id = "proposal-" + uuid.uuid4().hex
    safe_context = {"retrieved": bool(rag.get("retrieved")), "query_id": rag.get("query_id"), "sources": len(rag.get("hits", [])) if isinstance(rag.get("hits"), list) else rag.get("selected_chunks"), "ranking_version": rag.get("ranking_version"), "context_budget": rag.get("context_budget", "SMALL")}
    skill = OPERATION_SKILLS[operation_id]
    policy = skill_config(skill)
    proposal = {"proposal_id": proposal_id, "project_id": project_id, "operation_id": operation_id, "skill": skill, "template_version": "2.0.0", "parameters": clean, "status": "PROPOSAL_READY", "mutates": operation["mutates"], "requires_checkpoint": bool(policy.get("requires_checkpoint", False)), "human_gate": bool(policy.get("human_gate", False)), "allowed_agents": list(policy["allowed_agents"]), "rag": safe_context, "model_requested": metrics.get("initial", {}).get("model") or "UNKNOWN/NOT_CONFIRMED", "reasoning": metrics.get("initial", {}).get("reasoning") or "UNKNOWN/NOT_CONFIRMED", "context_budget": metrics.get("initial", {}).get("context_budget") or "SMALL", "provider": provider, "agents": [], "metrics": {"credits": "UNKNOWN/NOT_OBSERVED", "tokens": "UNKNOWN/NOT_OBSERVED"}, "evidence_refs": [safe_context.get("query_id") or "UNKNOWN/NOT_CONFIRMED"], "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    proposal["proposal_hash"] = _hash(proposal)
    return proposal


def proposal_store(path: Path, proposal: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(proposal, ensure_ascii=False, sort_keys=True) + "\n")


def read_proposals(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
    return rows
