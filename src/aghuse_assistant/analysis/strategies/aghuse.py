from __future__ import annotations

from .generic import GenericStrategy
from ..models import DemandContext


class AghuseStrategy(GenericStrategy):
    AREAS = ("entidade", "DAO", "ON/RN", "EJB", "XHTML", "segurança", "banco", "testes")

    def stages(self, demand: DemandContext) -> tuple[dict, ...]:
        objective = demand.objective.casefold()
        area_markers = {
            "segurança": ("seguran", "autoriz", "permiss", "login"), "banco": ("banco", "sql", "migra"),
            "testes": ("teste", "qualidade"), "XHTML": ("tela", "xhtml", "interface"),
        }
        stages = [{"area": "código", "capability": "analysis", "preferred_tools": ("code.search", "git.search"), "required": True}]
        stages.extend(
            {"area": area, "capability": "analysis", "preferred_tools": ("code.search", "git.search"), "required": any(marker in objective for marker in area_markers.get(area, (area.casefold(),)))}
            for area in self.AREAS
        )
        if demand.references:
            stages.insert(0, {"area": "requisito externo", "capability": "analysis", "preferred_tools": ("redmine.search",)})
        return tuple(stages)
