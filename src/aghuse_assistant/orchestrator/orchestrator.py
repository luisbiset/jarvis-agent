from __future__ import annotations

from typing import Any

from ..gateway import ToolGateway
from ..operations.catalog import OPERATIONS, validate
from ..policy.permissions import can_execute
from ..teams import AnalysisTeam, DevelopmentTeam, MaintenanceTeam, PlanningTeam, QATeam
from .models import ExecutionAuthorization, ExecutionContext, ExecutionResult, ExecutionState


class Orchestrator:
    """Small deterministic coordinator; the Codex remains the LLM authority."""

    def __init__(self, teams: dict[str, Any] | None = None, gateway: ToolGateway | None = None) -> None:
        self.gateway = gateway or ToolGateway()
        self.teams = teams or {
            "ANALYZE": AnalysisTeam(self.gateway),
            "PLAN": PlanningTeam(self.gateway),
            "IMPLEMENT": DevelopmentTeam(self.gateway),
            "MANUTENCAO": MaintenanceTeam(self.gateway),
            "VALIDATE": QATeam(self.gateway),
        }

    def create(self, payload: dict[str, Any]) -> ExecutionContext:
        operation = str(payload.get("operation", "")).upper()
        project = payload.get("project", "aghuse")
        objective = payload.get("objective", "")
        validate(operation, {"objective": objective})
        if operation not in OPERATIONS:
            raise ValueError(f"unsupported operation: {operation}")
        return ExecutionContext(project, operation, objective, payload.get("task_ref"), payload.get("parameters", {}), payload.get("artifacts", {}))

    def execute(self, context: ExecutionContext, *, confirm: bool = False) -> ExecutionResult:
        if context.operation in {"IMPLEMENT", "MANUTENCAO"} and not confirm:
            return ExecutionResult(context.operation, context.project, context.execution_id, ExecutionState.WAITING_INPUT, "Explicit confirmation required", {"approval_required": True})
        team = self.teams.get(context.operation)
        if team is None:
            return ExecutionResult(context.operation, context.project, context.execution_id, ExecutionState.SUCCEEDED, "Operation prepared by orchestrator", {"objective": context.objective, "mutates": False})
        if not can_execute(context.operation, "edit_files") and context.operation in {"IMPLEMENT", "MANUTENCAO"}:
            raise PermissionError(f"operation denied: {context.operation}")
        authorization = ExecutionAuthorization(mutation_confirmed=confirm)
        return team.execute(context, authorization)

    def cancel(self, context: ExecutionContext) -> ExecutionResult:
        return ExecutionResult(context.operation, context.project, context.execution_id, ExecutionState.CANCELLED, "Execution cancelled")
