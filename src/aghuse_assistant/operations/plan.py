"""Stable PLAN operation facade."""
from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext, ExecutionResult, ExecutionState
from ..planning import PlanningEngine, PlanningInputError, to_execution

OPERATION_ID = "PLAN"
SKILL = "planejar"


def execute(context: ExecutionContext, gateway: ToolGateway, _authorization: ExecutionAuthorization) -> ExecutionResult:
    try:
        plan, warnings = PlanningEngine().execute(context, gateway)
    except (PlanningInputError, ValueError) as exc:
        return ExecutionResult(OPERATION_ID, context.project, context.execution_id, ExecutionState.WAITING_INPUT, str(exc), {"required_artifact": "analysis", "required_status": "COMPLETE"})
    return to_execution(context, plan, warnings)


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": False}
