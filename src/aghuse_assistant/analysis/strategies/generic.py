from __future__ import annotations

from ..models import DemandContext


class GenericStrategy:
    def stages(self, demand: DemandContext) -> tuple[dict, ...]:
        stages = [{"area": "código", "capability": "analysis", "preferred_tools": ("code.search", "git.search")}]
        if demand.references:
            stages.append({"area": "requisito externo", "capability": "analysis", "preferred_tools": ("redmine.search",)})
        return tuple(stages)
