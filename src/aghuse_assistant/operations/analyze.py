"""Stable ANALYZE operation facade."""
from __future__ import annotations

from ..analysis import AnalysisEngine, to_execution
from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionContext, ExecutionResult

OPERATION_ID = "ANALYZE"
SKILL = "analisar"


def execute(context: ExecutionContext, gateway: ToolGateway) -> ExecutionResult:
    return to_execution(context, AnalysisEngine().execute(context, gateway))


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": False}
