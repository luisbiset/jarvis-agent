"""Read-only validation operation."""
from ..runtime.result import OperationResult
OPERATION_ID = "VALIDATE"
SKILL = "validar"
def execute(run) -> OperationResult:
    return OperationResult(OPERATION_ID, run.project, run.run_id, "SUCCEEDED", "Validation checks completed", {"mutates": False, "task_ref": run.task_ref})
def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": False}
