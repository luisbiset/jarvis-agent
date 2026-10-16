from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import MaintenanceResult


def to_execution(context: ExecutionContext, result: MaintenanceResult) -> ExecutionResult:
    summary = "Manutenção concluída" if not result.pending_items else "Manutenção concluída com pendências"
    return ExecutionResult("MANUTENCAO", context.project, context.execution_id, ExecutionState.SUCCEEDED, summary, result.to_dict(), list(result.pending_items))
