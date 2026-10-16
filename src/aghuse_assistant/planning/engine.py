from __future__ import annotations

from ..analysis.models import AnalysisResult
from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionContext
from .models import PlanResult
from .planner import build


class PlanningInputError(ValueError):
    pass


class PlanningEngine:
    def execute(self, context: ExecutionContext, gateway: ToolGateway) -> tuple[PlanResult, list[str]]:
        raw = context.artifacts.get("analysis")
        if raw is None:
            raise PlanningInputError("AnalysisResult obrigatório")
        analysis = AnalysisResult.from_dict(raw)
        if analysis.coverage.status != "COMPLETE":
            raise PlanningInputError("AnalysisResult deve estar COMPLETE")
        warnings: list[str] = []
        for tool in gateway.select(capability="planning", read_only=True):
            result = gateway.invoke(tool.name, analysis=raw, objective=context.objective)
            if result.status != "SUCCEEDED":
                warnings.append(f"{tool.name}: {result.warning or result.status}")
        return build(analysis), warnings
