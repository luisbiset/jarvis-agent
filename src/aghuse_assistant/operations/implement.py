"""Stable IMPLEMENT operation facade."""
from ..gateway import ToolGateway
from ..implementation import ImplementationEngine, ImplementationInputError, to_execution
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext, ExecutionResult, ExecutionState

OPERATION_ID = "IMPLEMENT"
SKILL = "implementar"


def execute(context: ExecutionContext, gateway: ToolGateway, authorization: ExecutionAuthorization) -> ExecutionResult:
    try:
        return to_execution(context, ImplementationEngine().execute(context, gateway, authorization))
    except (ImplementationInputError, ValueError) as exc:
        return ExecutionResult(OPERATION_ID, context.project, context.execution_id, ExecutionState.WAITING_INPUT, str(exc), {"approval_required": not authorization.mutation_confirmed})


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": True}
