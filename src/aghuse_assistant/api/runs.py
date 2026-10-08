"""Run API service independent of any web framework."""
from ..runtime import OperationDispatcher, OperationRun, RunStore
from ..operations import analyze, implement, plan, maintenance
from ..operations.validate import execute as validate_execute
from .projects import list_projects
from ..runtime.provider import StructuredProvider
from ..runtime.responses import deterministic
from ..runtime.renderers import render

HANDLERS = {"ANALYZE": analyze.execute, "PLAN": plan.execute, "IMPLEMENT": implement.execute, "VALIDATE": validate_execute, "MANUTENCAO": maintenance.execute}


class RunService:
    def __init__(self, dispatcher: OperationDispatcher | None = None, provider=None) -> None:
        self.dispatcher = dispatcher or OperationDispatcher(RunStore())
        self.provider = provider or StructuredProvider()

    def create(self, payload: dict) -> dict:
        project = payload.get("project", "aghuse")
        if project not in {item["project_id"] for item in list_projects()}:
            raise ValueError(f"unknown project: {project}")
        run = self.dispatcher.create(
            project=project,
            operation=payload["operation"],
            objective=payload["objective"],
            task_ref=payload.get("task_ref"),
            context_refs=payload.get("context_refs", []),
        )
        return run.as_dict()

    def get(self, run_id: str) -> dict | None:
        run = self.dispatcher.store.get(run_id)
        return run.as_dict() if run else None

    def list(self) -> list[dict]:
        return [run.as_dict() for run in self.dispatcher.store.list()]

    def cancel(self, run_id: str) -> dict:
        return self.dispatcher.cancel(run_id).as_dict()

    def execute(self, run_id: str) -> dict:
        run = self.dispatcher.store.get(run_id)
        if run is None:
            raise KeyError(run_id)
        result = self.dispatcher.execute(run, lambda current: self._execute_structured(current))
        return {"run": run.as_dict(), "result": result.as_dict()}

    def present(self, run_id: str) -> str:
        return render(self.execute(run_id)["result"])

    def present_result(self, execution: dict) -> str:
        return render(execution["result"])

    def _execute_structured(self, run):
        if self.provider is None:
            payload = deterministic(run.operation, run)
        else:
            schema = {"operation": run.operation, "required_data_fields": __import__("aghuse_assistant.runtime.responses", fromlist=["OPERATIONS"]).OPERATIONS[run.operation]}
            payload = self.provider.execute(run, schema)
        from ..runtime.result import OperationResult
        return OperationResult(run.operation, run.project, run.run_id, payload["status"], payload["summary"], payload["data"], payload["warnings"], payload["evidence"], payload["validation"])
