from __future__ import annotations

from typing import Any

from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext
from .models import ImplementationResult
from .rollback import notes


def execute(context: ExecutionContext, gateway: ToolGateway, authorization: ExecutionAuthorization, actions: list[dict[str, Any]]) -> ImplementationResult:
    changes: list[dict[str, Any]] = []
    files: list[str] = []
    tests: list[str] = []
    passed: list[str] = []
    pending: list[str] = []
    failures: list[str] = []
    tools = gateway.select(capability="implementation")
    if not tools:
        pending.append("Nenhuma ferramenta de implementação registrada")
    for action in actions:
        for tool in tools:
            if not tool.read_only and not authorization.mutation_confirmed:
                pending.append(f"{tool.name}: confirmação de mutação obrigatória")
                continue
            result = gateway.invoke(tool.name, confirm=authorization.mutation_confirmed, action=action, context={"project": context.project, "objective": context.objective})
            if result.status != "SUCCEEDED":
                failures.append(tool.name)
                pending.append(f"{tool.name}: {result.warning or result.status}")
                continue
            payload = result.data if isinstance(result.data, dict) else {}
            changes.extend(payload.get("changes", [action]))
            files.extend(payload.get("files_changed", []))
            tests.extend(payload.get("tests_executed", []))
            passed.extend(payload.get("tests_passed", []))
    return ImplementationResult(tuple(changes), tuple(sorted(set(files))), tuple(tests), tuple(passed), tuple(pending), notes(files, failures), False)
