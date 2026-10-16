from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import PlanResult


def to_execution(context: ExecutionContext, plan: PlanResult, warnings: list[str]) -> ExecutionResult:
    data = plan.to_dict()
    data.pop("approved", None)
    return ExecutionResult("PLAN", context.project, context.execution_id, ExecutionState.SUCCEEDED, "Plano técnico preparado", data, warnings)
