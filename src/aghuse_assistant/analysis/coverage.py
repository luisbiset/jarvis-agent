from __future__ import annotations

from .evidence import is_confirmed
from .models import Coverage, DemandContext, InvestigationTrace


def evaluate(demand: DemandContext, trace: InvestigationTrace, impact_count: int) -> Coverage:
    covered = {item.get("requirement_id") for item in trace.findings if is_confirmed(item)}
    pending = tuple(requirement.id for requirement in demand.requirements if requirement.required and requirement.id not in covered)
    unsupported = sum(1 for item in trace.findings if item.get("type") not in {"INFERENCE", "ACCESS_LIMITATION"} and not is_confirmed(item))
    if pending and trace.limitations and not covered:
        status = "BLOCKED"
    elif pending or unsupported or trace.budget_exhausted or trace.limitations:
        status = "PARTIAL"
    else:
        status = "COMPLETE"
    return Coverage(status, len(demand.requirements), len(demand.requirements) - len(pending), pending, unsupported, impact_count, tuple(trace.limitations))
