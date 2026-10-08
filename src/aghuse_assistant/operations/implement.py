"""Controlled implementation operation."""
from ..runtime.result import OperationResult
OPERATION_ID = "IMPLEMENT"
SKILL = "implementar"
def execute(run) -> OperationResult:
    return OperationResult(OPERATION_ID, run.project, run.run_id, "SUCCEEDED", "Implementation operation authorized", {"mutates": True, "task_ref": run.task_ref})
def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": True}
