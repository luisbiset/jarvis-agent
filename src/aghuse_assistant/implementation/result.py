from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import ImplementationResult


def to_execution(context: ExecutionContext, result: ImplementationResult) -> ExecutionResult:
    summary = "Implementação concluída" if not result.pending_items else "Implementação concluída com pendências"
    return ExecutionResult("IMPLEMENT", context.project, context.execution_id, ExecutionState.SUCCEEDED, summary, result.to_dict(), list(result.pending_items))
