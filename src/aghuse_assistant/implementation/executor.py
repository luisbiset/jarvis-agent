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
    completed: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    tools = tuple(tool for tool in gateway.select(capability="implementation") if not tool.read_only and tool.scope == "workspace" and tool.rollback_handler is not None)
    if not tools:
        pending.append("Nenhuma ferramenta mutável de escopo workspace com rollback registrada")
        return ImplementationResult((), (), (), (), tuple(pending), notes([], [], []), False)
    selected: list[tuple[dict[str, Any], str]] = []
    for action in actions:
        requested = action.get("tool")
        candidates = tuple(tool for tool in tools if tool.name == requested) if requested else tools
        if len(candidates) != 1:
            pending.append(f"{action.get('id', 'ação')}: roteamento de ferramenta ausente ou ambíguo")
            return ImplementationResult((), (), (), (), tuple(pending), notes([], [], []), False)
        selected.append((action, candidates[0].name))
    failures: list[str] = []
    rollback_failures: list[str] = []
    for action, tool_name in selected:
        result = gateway.invoke(tool_name, confirm=authorization.mutation_confirmed, action=action, context={"project": context.project, "objective": context.objective})
        if result.status != "SUCCEEDED" or not isinstance(result.data, dict):
            failures.append(tool_name)
            pending.append(f"{tool_name}: {result.warning or result.status if result.status != 'SUCCEEDED' else 'resposta inválida'}")
            for completed_tool, completed_action, completed_payload in reversed(completed):
                rollback = gateway.rollback(completed_tool, confirm=authorization.mutation_confirmed, action=completed_action, context={"project": context.project, "objective": context.objective}, result=completed_payload)
                if rollback.status != "SUCCEEDED":
                    rollback_failures.append(f"{completed_tool}: {rollback.warning or rollback.status}")
            if not rollback_failures:
                changes.clear()
                files.clear()
                tests.clear()
                passed.clear()
            break
        payload = result.data
        completed.append((tool_name, action, payload))
        changes.extend(payload.get("changes", [action]))
        files.extend(payload.get("files_changed", []))
        tests.extend(payload.get("tests_executed", []))
        passed.extend(payload.get("tests_passed", []))
    return ImplementationResult(tuple(changes), tuple(sorted(set(files))), tuple(tests), tuple(passed), tuple(pending), notes(files, failures, rollback_failures), False)
