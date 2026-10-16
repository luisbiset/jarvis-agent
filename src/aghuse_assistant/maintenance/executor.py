from __future__ import annotations

from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext
from .models import MaintenanceResult


def execute(context: ExecutionContext, gateway: ToolGateway, authorization: ExecutionAuthorization) -> MaintenanceResult:
    changes = []
    files = []
    tests = []
    passed = []
    pending = []
    tools = gateway.select(capability="maintenance")
    if not tools:
        pending.append("Nenhuma ferramenta de manutenção registrada")
    for tool in tools:
        if tool.scope not in {"assistant-only", "workspace"}:
            pending.append(f"{tool.name}: escopo externo bloqueado")
            continue
        if not tool.read_only and not authorization.mutation_confirmed:
            pending.append(f"{tool.name}: confirmação de mutação obrigatória")
            continue
        result = gateway.invoke(tool.name, confirm=authorization.mutation_confirmed, objective=context.objective)
        if result.status != "SUCCEEDED":
            pending.append(f"{tool.name}: {result.warning or result.status}")
            continue
        payload = result.data if isinstance(result.data, dict) else {}
        changes.extend(payload.get("changes", []))
        files.extend(payload.get("files_changed", []))
        tests.extend(payload.get("tests_executed", []))
        passed.extend(payload.get("tests_passed", []))
    rollback = "Nenhuma alteração observada; rollback não necessário." if not files else "Reverter os arquivos desta manutenção: " + ", ".join(sorted(set(files))) + "."
    return MaintenanceResult(tuple(changes), tuple(sorted(set(files))), tuple(tests), tuple(passed), tuple(pending), rollback)
