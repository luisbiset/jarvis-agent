from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import ValidationResult


def to_execution(context: ExecutionContext, result: ValidationResult) -> ExecutionResult:
    summary = "Validação concluída" if not result.failed else "Validação concluída com falhas"
    return ExecutionResult("VALIDATE", context.project, context.execution_id, ExecutionState.SUCCEEDED, summary, result.to_dict(), list(result.warnings), list(result.evidence))
