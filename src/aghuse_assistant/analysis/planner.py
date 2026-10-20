from __future__ import annotations

from .models import DemandContext, InvestigationPlan, InvestigationStep


def plan(demand: DemandContext, strategy) -> InvestigationPlan:
    steps: list[InvestigationStep] = []
    for requirement in demand.requirements:
        previous: str | None = None
        for index, stage in enumerate(strategy.stages(demand), 1):
            step_id = f"{requirement.id}-S{index:02d}"
            steps.append(InvestigationStep(
                id=step_id,
                requirement_id=requirement.id,
                area=stage["area"],
                capability=stage["capability"],
                query=f"{stage['area']}: {requirement.text}",
                preferred_tools=tuple(stage.get("preferred_tools", ())),
                depends_on=(previous,) if previous else (),
                required_area=bool(stage.get("required", True)),
            ))
            previous = step_id
    return InvestigationPlan(tuple(steps))
