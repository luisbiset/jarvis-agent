"""Stable VALIDATE operation facade."""
from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext, ExecutionResult, ExecutionState
from ..validation import ValidationEngine, ValidationInputError, to_execution

OPERATION_ID = "VALIDATE"
SKILL = "validar"


def execute(context: ExecutionContext, gateway: ToolGateway, _authorization: ExecutionAuthorization) -> ExecutionResult:
    try:
        return to_execution(context, ValidationEngine().execute(context, gateway))
    except (ValidationInputError, ValueError) as exc:
        return ExecutionResult(OPERATION_ID, context.project, context.execution_id, ExecutionState.WAITING_INPUT, str(exc), {"required": "ImplementationResult ou contexto explícito"})


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": False}
