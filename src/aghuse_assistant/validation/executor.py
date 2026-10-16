from __future__ import annotations

from dataclasses import asdict

from ..gateway import ToolGateway
from .models import ValidationCheck, ValidationResult


def execute(checks: tuple[ValidationCheck, ...], gateway: ToolGateway) -> ValidationResult:
    passed = []
    failed = []
    warnings: list[str] = []
    regressions = []
    evidence = []
    tools = gateway.select(capability="validation", read_only=True)
    if not tools:
        warnings.append("Nenhuma ferramenta de validação somente leitura registrada")
    for check in checks:
        for tool in tools:
            result = gateway.invoke(tool.name, check=asdict(check))
            if result.status != "SUCCEEDED":
                failed.append({"check_id": check.id, "tool": tool.name, "description": result.warning or result.status, "critical": True})
                continue
            payload = result.data if isinstance(result.data, dict) else {}
            status = payload.get("status", "PASSED")
            item = {"check_id": check.id, "tool": tool.name, "description": payload.get("description", check.description)}
            if status == "FAILED":
                item["critical"] = bool(payload.get("critical", False))
                failed.append(item)
            else:
                passed.append(item)
            warnings.extend(str(value) for value in payload.get("warnings", []))
            regressions.extend(value for value in payload.get("regressions", []) if isinstance(value, dict))
            evidence.extend(value for value in payload.get("evidence", []) if isinstance(value, dict))
    critical = any(item.get("critical") for item in failed)
    recommendation = "Retornar ao desenvolvimento" if critical or regressions else ("Aprovar com ressalvas" if failed or warnings else "Aprovar")
    return ValidationResult(tuple(asdict(check) for check in checks), tuple(passed), tuple(failed), tuple(warnings), tuple(regressions), tuple(evidence), recommendation)
