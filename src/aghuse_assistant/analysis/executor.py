from __future__ import annotations

from collections import deque
from typing import Any

from ..gateway import ToolGateway
from .evidence import normalize
from .models import InvestigationLimits, InvestigationPlan, InvestigationStep, InvestigationTrace


def execute(plan: InvestigationPlan, gateway: ToolGateway, limits: InvestigationLimits) -> InvestigationTrace:
    trace = InvestigationTrace()
    queue = deque(plan.steps)
    seen: set[tuple[str, str, str]] = set()
    completed: set[str] = set()

    while queue:
        step = queue.popleft()
        key = (step.requirement_id, step.area, step.query)
        if key in seen:
            continue
        if any(dependency not in completed for dependency in step.depends_on):
            trace.limitations.append(f"{step.id}: dependência não concluída")
            continue
        if len(trace.executed_steps) >= limits.max_steps or trace.tool_calls >= limits.max_tool_calls:
            trace.limitations.append("Limite da investigação atingido antes da conclusão do plano")
            trace.budget_exhausted = True
            break
        seen.add(key)
        trace.executed_steps.append(step.id)
        tools = _tools_for(step, gateway)
        if not tools:
            trace.limitations.append(f"{step.area}: nenhuma ferramenta somente leitura disponível")
            completed.add(step.id)
            continue
        trace.searched_terms.append(step.query)
        trace.areas_examined.append(step.area)

        step_findings: list[dict[str, Any]] = []
        successful_call = False
        for tool in tools:
            if trace.tool_calls >= limits.max_tool_calls:
                trace.limitations.append("Limite de chamadas de ferramenta atingido")
                trace.budget_exhausted = True
                break
            trace.tool_calls += 1
            result = gateway.invoke(tool.name, query={
                "step_id": step.id,
                "requirement_id": step.requirement_id,
                "area": step.area,
                "term": step.query,
                "stop_condition": step.stop_condition,
            })
            if result.status != "SUCCEEDED":
                trace.limitations.append(f"{step.area}/{tool.name}: {result.warning or result.status}")
                continue
            successful_call = True
            payload = result.data if isinstance(result.data, list) else [result.data]
            for item in payload:
                if isinstance(item, dict):
                    step_findings.append(normalize(item, step.requirement_id))

        if successful_call and not step_findings:
            trace.no_occurrences.append(f"{step.area}: {step.query}")
        remaining = max(0, limits.max_findings - len(trace.findings))
        retained = step_findings[:remaining]
        trace.findings.extend(retained)
        _enqueue_follow_ups(queue, step, retained)
        completed.add(step.id)
        if len(trace.findings) >= limits.max_findings:
            trace.limitations.append("Limite de achados atingido")
            trace.budget_exhausted = True
            break
    return trace


def _tools_for(step: InvestigationStep, gateway: ToolGateway):
    candidates = gateway.select(capability=step.capability, read_only=True)
    if not step.preferred_tools:
        return candidates
    preferred = set(step.preferred_tools)
    return tuple(tool for tool in candidates if tool.name in preferred)


def _enqueue_follow_ups(queue, parent: InvestigationStep, findings: list[dict[str, Any]]) -> None:
    sequence = 0
    for finding in findings:
        for follow_up in finding.get("follow_up_queries", []) if isinstance(finding.get("follow_up_queries"), list) else []:
            if not isinstance(follow_up, dict) or not follow_up.get("term"):
                continue
            sequence += 1
            queue.append(InvestigationStep(
                id=f"{parent.id}-F{sequence:02d}",
                requirement_id=str(follow_up.get("requirement_id") or parent.requirement_id),
                area=str(follow_up.get("area") or parent.area),
                capability=str(follow_up.get("capability") or parent.capability),
                query=str(follow_up["term"]),
                preferred_tools=tuple(follow_up.get("preferred_tools") or parent.preferred_tools),
                depends_on=(parent.id,),
            ))
