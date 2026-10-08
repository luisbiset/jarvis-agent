"""Read-only analysis operation."""
from ..runtime.result import OperationResult
from .analyze_contract import InvestigationQuestion, InvestigationLimits, interpret_demand, investigate_progressively, metrics, to_dict, validate_coverage
OPERATION_ID = "ANALYZE"
SKILL = "analisar"
def execute(run) -> OperationResult:
    context = interpret_demand(run.objective, references=[run.task_ref] if run.task_ref else None)
    adapter = getattr(run, "analysis_adapter", None)
    questions = [InvestigationQuestion(f"Q-{index:02d}", requirement.id, f"What happens in the flow related to: {requirement.text}?") for index, requirement in enumerate(context.requirements, 1)]
    queries = [{"area": "demand", "term": question.question, "requirement_id": question.requirement_id, "question_id": question.id} for question in questions]
    trace = investigate_progressively(queries, adapter, limits=getattr(run, "analysis_limits", None)) if adapter else None
    findings = trace.findings if trace else []
    limitations = trace.limitations if trace else ["No repository/MCP adapter was supplied to this read-only core."]
    impact_matrix = []
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("component") or not finding.get("classification"):
            continue
        impact_matrix.append({"component": finding["component"], "role": finding.get("role", "UNKNOWN/NOT_CONFIRMED"), "classification": finding["classification"], "change": finding.get("change", "UNKNOWN/NOT_CONFIRMED"), "justification": finding.get("justification", finding.get("conclusion", "UNKNOWN/NOT_CONFIRMED")), "evidence": finding.get("evidence", []), "status": finding.get("status", "PARTIAL")})
    coverage = validate_coverage(context.requirements, findings, impact_matrix, limitations=limitations, access_blocked=bool(trace and trace.limitations and not findings))
    observed_metrics = metrics(mcp_calls=trace.calls if trace else 0)
    observed_metrics.update({"requirements_total": coverage["requirements_total"], "questions_total": len(questions), "questions_concluded": len(questions) - len(coverage["requirements_pending"]), "questions_blocked": 0, "findings_discovered": len(findings), "findings_verified": sum(1 for item in findings if item.get("type") in {"CODE", "DATA", "DOCUMENTATION"}), "budget_exhausted": any("limit" in item.casefold() for item in limitations)})
    data = {
        "mutates": False, "analysis_context": run.objective, "task_ref": run.task_ref,
        "requirements": [item for item in to_dict(context)["requirements"]],
        "questions": [{"id": q.id, "requirement_id": q.requirement_id, "question": q.question, "scope": q.scope, "stop_condition": q.stop_condition, "status": "CONCLUDED" if q.requirement_id not in coverage["requirements_pending"] else "OPEN"} for q in questions],
        "investigation_objective": context.investigation_objective,
        "findings": findings, "impact": "UNKNOWN/NOT_CONFIRMED", "impact_matrix": impact_matrix,
        "coverage": {"analyzed": trace.areas_examined if trace else [], "pending": coverage["requirements_pending"], "no_occurrences": trace.no_occurrences if trace else [], "not_investigated": [], "searched_terms": trace.searched_terms if trace else [], "limitations": limitations, **coverage},
        "affected_files": [], "risks": [{"severity": "MEDIUM", "description": "Technical conclusions require evidence from configured adapters."}],
        "recommendations": ["Run investigation adapters and attach evidence before declaring COMPLETE."], "evidence": [], "metrics": observed_metrics, "investigation_status": coverage["status"],
    }
    return OperationResult(OPERATION_ID, run.project, run.run_id, "SUCCEEDED", "Demand interpreted; technical investigation pending evidence", data)
def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": False}
