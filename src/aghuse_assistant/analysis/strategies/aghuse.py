from __future__ import annotations

from .generic import GenericStrategy
from ..models import DemandContext


class AghuseStrategy(GenericStrategy):
    AREAS = ("entidade", "DAO", "ON/RN", "EJB", "XHTML", "segurança", "banco", "testes")

    def stages(self, demand: DemandContext) -> tuple[dict, ...]:
        stages = [
            {"area": area, "capability": "analysis", "preferred_tools": ("code.search", "git.search")}
            for area in self.AREAS
        ]
        if demand.references:
            stages.insert(0, {"area": "requisito externo", "capability": "analysis", "preferred_tools": ("redmine.search",)})
        return tuple(stages)
