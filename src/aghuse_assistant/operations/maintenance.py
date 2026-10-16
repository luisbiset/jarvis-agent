"""Stable MANUTENCAO operation facade."""
from ..gateway import ToolGateway
from ..maintenance import MaintenanceEngine, MaintenanceInputError, to_execution
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext, ExecutionResult, ExecutionState

OPERATION_ID = "MANUTENCAO"
SKILL = "manutencao"
AGENT = "aghuse_assistant"


def execute(context: ExecutionContext, gateway: ToolGateway, authorization: ExecutionAuthorization) -> ExecutionResult:
    try:
        return to_execution(context, MaintenanceEngine().execute(context, gateway, authorization))
    except (MaintenanceInputError, ValueError) as exc:
        return ExecutionResult(OPERATION_ID, context.project, context.execution_id, ExecutionState.WAITING_INPUT, str(exc), {"scope": "assistant-only", "agent": AGENT, "approval_required": not authorization.mutation_confirmed})


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": True, "agent": AGENT, "scope": "assistant-only"}
