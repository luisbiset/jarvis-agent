from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import ImplementationResult


def to_execution(context: ExecutionContext, result: ImplementationResult) -> ExecutionResult:
    failed = bool(result.pending_items)
    summary = "Implementação bloqueada ou revertida" if failed else "Implementação concluída"
    return ExecutionResult("IMPLEMENT", context.project, context.execution_id, ExecutionState.FAILED if failed else ExecutionState.SUCCEEDED, summary, result.to_dict(), list(result.pending_items))
