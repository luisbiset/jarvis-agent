"""Stable ANALYZE operation facade."""
from __future__ import annotations

from ..analysis import AnalysisEngine, to_execution
from ..analysis.models import AnalysisResult
from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionContext, ExecutionResult

OPERATION_ID = "ANALYZE"
SKILL = "analisar"


def execute(context: ExecutionContext, gateway: ToolGateway) -> ExecutionResult:
    return to_execution(context, execute_artifact(context, gateway))


def execute_artifact(context: ExecutionContext, gateway: ToolGateway) -> AnalysisResult:
    """Run analysis and retain its serializable artifact for an in-process consumer."""
    return AnalysisEngine().execute(context, gateway)


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": False}
