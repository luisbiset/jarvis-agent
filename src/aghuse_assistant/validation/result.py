from ..orchestrator.models import ExecutionContext, ExecutionResult, ExecutionState
from .models import ValidationResult


def to_execution(context: ExecutionContext, result: ValidationResult) -> ExecutionResult:
    blocking = bool(result.regressions) or any(item.get("critical") for item in result.failed)
    state = ExecutionState.FAILED if blocking else ExecutionState.SUCCEEDED
    summary = "Validação bloqueada por falhas críticas ou regressões" if blocking else ("Validação concluída" if not result.failed else "Validação concluída com falhas")
    return ExecutionResult("VALIDATE", context.project, context.execution_id, state, summary, result.to_dict(), list(result.warnings), list(result.evidence))
