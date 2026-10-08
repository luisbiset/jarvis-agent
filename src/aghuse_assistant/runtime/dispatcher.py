"""Dispatches an operation without imposing a business workflow."""
from __future__ import annotations

from typing import Any

from ..operations import validate
from ..policy.permissions import can_execute
from .run import OperationRun, RunStatus
from .store import RunStore
from .result import OperationResult

OPERATIONS = {"ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE", "MANUTENCAO"}


class OperationDispatcher:
    def __init__(self, store: RunStore | None = None) -> None:
        self.store = store or RunStore()

    def create(self, project: str, operation: str, objective: str, **kwargs: Any) -> OperationRun:
        operation = operation.upper()
        if operation not in OPERATIONS:
            raise ValueError(f"unsupported operation: {operation}")
        if not objective.strip():
            raise ValueError("objective cannot be empty")
        validate(operation, {"objective": objective})
        run = OperationRun(project=project, operation=operation, objective=objective, **kwargs)
        return self.store.save(run)

    def start(self, run: OperationRun) -> OperationRun:
        if not can_execute(run.operation, "start"):
            raise PermissionError(f"operation denied: {run.operation}")
        run.start()
        return self.store.save(run)

    def execute(self, run: OperationRun, handler) -> OperationResult:
        self.start(run)
        try:
            result = handler(run)
            run.finish(RunStatus.SUCCEEDED, result_ref=run.run_id)
            # Execution success and investigation sufficiency are independent.
            if isinstance(result.data, dict):
                technical = result.data.get("investigation_status")
                if technical in {"PARTIAL", "BLOCKED", "FAILED"}:
                    result.data.setdefault("run_status", "SUCCEEDED")
                    result.data.setdefault("technical_status", technical)
            self.store.save(run)
            return result
        except Exception:
            run.finish(RunStatus.FAILED)
            self.store.save(run)
            raise

    def cancel(self, run_id: str) -> OperationRun:
        run = self.store.get(run_id)
        if run is None:
            raise KeyError(run_id)
        run.finish(status=RunStatus.CANCELLED)
        return self.store.save(run)
