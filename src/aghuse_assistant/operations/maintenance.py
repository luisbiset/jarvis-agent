"""Controlled maintenance operation for the AGHUse Assistant itself."""
from ..runtime.result import OperationResult

OPERATION_ID = "MANUTENCAO"
SKILL = "manutencao"
AGENT = "aghuse_assistant"


def execute(run) -> OperationResult:
    return OperationResult(
        OPERATION_ID,
        run.project,
        run.run_id,
        "SUCCEEDED",
        "Maintenance operation authorized for the AGHUse Assistant scope",
        {
            "mutates": True,
            "agent": AGENT,
            "scope": "assistant-only",
            "task_ref": run.task_ref,
            "approval_required": True,
            "changes": [],
            "files_changed": [],
            "tests_executed": [],
            "tests_passed": [],
            "pending_items": ["Human checkpoint required before changes"],
            "rollback_notes": "No changes executed by the operation shell.",
        },
    )


def preview(project_id, parameters, **_):
    return {"operation": OPERATION_ID, "project": project_id, "parameters": parameters, "mutates": True, "agent": AGENT, "scope": "assistant-only"}
