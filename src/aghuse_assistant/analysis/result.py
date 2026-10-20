from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import AnalysisResult


def to_execution(context: ExecutionContext, result: AnalysisResult) -> ExecutionResult:
    coverage = result.coverage
    questions = _questions(result)
    data: dict[str, Any] = {
        "mutates": False,
        "analysis_context": context.objective,
        "task_ref": context.task_ref,
        "requirements": [asdict(requirement) for requirement in result.demand.requirements],
        "questions": questions,
        "investigation_objective": result.demand.investigation_objective,
        "findings": list(result.findings),
        "impact": "UNKNOWN/NOT_CONFIRMED",
        "impact_matrix": list(result.impact_matrix),
        "coverage": {
            "analyzed": result.trace.areas_examined,
            "pending": list(coverage.requirements_pending),
            "no_occurrences": result.trace.no_occurrences,
            "not_investigated": _not_investigated(result),
            "searched_terms": result.trace.searched_terms,
            "status": coverage.status,
            "requirements_total": coverage.requirements_total,
            "requirements_covered": coverage.requirements_covered,
            "requirements_pending": list(coverage.requirements_pending),
            "unsupported_findings": coverage.unsupported_findings,
            "impact_components": coverage.impact_components,
            "limitations": list(coverage.limitations),
            "required_areas": list(coverage.required_areas),
            "covered_areas": list(coverage.covered_areas),
            "pending_areas": list(coverage.pending_areas),
        },
        "affected_files": list(result.affected_files),
        "risks": [] if coverage.status == "COMPLETE" else [{"severity": "MEDIUM", "description": "Conclusões técnicas limitadas por evidências pendentes."}],
        "recommendations": [] if coverage.status == "COMPLETE" else ["Disponibilizar as ferramentas somente leitura indicadas pelo plano e anexar evidências verificáveis."],
        "evidence": list(result.evidence),
        "metrics": result.metrics,
        "investigation_status": coverage.status,
    }
    summary = "Análise técnica concluída com evidências verificadas" if coverage.status == "COMPLETE" else "Análise técnica concluída com evidências pendentes"
    return ExecutionResult("ANALYZE", context.project, context.execution_id, ExecutionState.SUCCEEDED, summary, data, list(coverage.limitations), list(result.evidence))


def _questions(result: AnalysisResult) -> list[dict[str, Any]]:
    pending = set(result.coverage.requirements_pending)
    questions = []
    for requirement in result.demand.requirements:
        steps = [step for step in result.plan.steps if step.requirement_id == requirement.id]
        questions.append({
            "id": f"Q-{requirement.id.removeprefix('REQ-')}",
            "requirement_id": requirement.id,
            "question": f"O que ocorre no fluxo relacionado a: {requirement.text}?",
            "scope": ", ".join(dict.fromkeys(step.area for step in steps)) or "código",
            "stop_condition": "evidência verificável ou bloqueio documentado",
            "status": "OPEN" if requirement.id in pending else "CONCLUDED",
        })
    return questions


def _not_investigated(result: AnalysisResult) -> list[str]:
    examined = set(result.trace.areas_examined)
    return list(dict.fromkeys(step.area for step in result.plan.steps if step.area not in examined))
