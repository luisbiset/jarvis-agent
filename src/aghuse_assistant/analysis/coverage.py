from __future__ import annotations

from .evidence import is_confirmed
from .models import Coverage, DemandContext, InvestigationPlan, InvestigationTrace


def evaluate(demand: DemandContext, plan: InvestigationPlan, trace: InvestigationTrace, impact_count: int) -> Coverage:
    required_by_requirement = {
        requirement.id: tuple(dict.fromkeys(step.area for step in plan.steps if step.requirement_id == requirement.id and step.required_area))
        for requirement in demand.requirements
    }
    covered_pairs = {(item.get("requirement_id"), item.get("area")) for item in trace.findings if is_confirmed(item)}
    pending = tuple(
        requirement.id for requirement in demand.requirements
        if requirement.required and any((requirement.id, area) not in covered_pairs for area in required_by_requirement[requirement.id])
    )
    required_areas = tuple(dict.fromkeys(area for areas in required_by_requirement.values() for area in areas))
    covered_areas = tuple(area for area in required_areas if all((requirement.id, area) in covered_pairs for requirement in demand.requirements if area in required_by_requirement[requirement.id]))
    pending_areas = tuple(area for area in required_areas if area not in covered_areas)
    unsupported = sum(1 for item in trace.findings if item.get("type") not in {"INFERENCE", "ACCESS_LIMITATION"} and not is_confirmed(item))
    covered = {requirement_id for requirement_id, _ in covered_pairs}
    if pending and trace.limitations and not covered:
        status = "BLOCKED"
    elif pending or unsupported or trace.budget_exhausted or trace.limitations:
        status = "PARTIAL"
    else:
        status = "COMPLETE"
    return Coverage(status, len(demand.requirements), len(demand.requirements) - len(pending), pending, unsupported, impact_count, tuple(trace.limitations), required_areas, covered_areas, pending_areas)
