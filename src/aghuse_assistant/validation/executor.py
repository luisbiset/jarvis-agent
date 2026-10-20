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
        failed.append({"check_id": "VALIDATION-TOOLING", "tool": "gateway", "description": "nenhuma ferramenta de validação disponível", "critical": True})
    for check in checks:
        for tool in tools:
            result = gateway.invoke(tool.name, check=asdict(check))
            if result.status != "SUCCEEDED":
                failed.append({"check_id": check.id, "tool": tool.name, "description": result.warning or result.status, "critical": True})
                continue
            payload = result.data if isinstance(result.data, dict) else None
            if payload is None:
                failed.append({"check_id": check.id, "tool": tool.name, "description": "resposta de validação inválida", "critical": True})
                continue
            item = {"check_id": check.id, "tool": tool.name, "description": payload.get("description", check.description)}
            status = payload.get("status")
            if status == "FAILED":
                item["critical"] = bool(payload.get("critical", False))
                failed.append(item)
            elif status == "PASSED":
                passed.append(item)
            else:
                item["description"] = f"status de validação inválido: {status!r}"
                item["critical"] = True
                failed.append(item)
            warnings.extend(str(value) for value in payload.get("warnings", []))
            regressions.extend(value for value in payload.get("regressions", []) if isinstance(value, dict))
            evidence.extend(value for value in payload.get("evidence", []) if isinstance(value, dict))
    critical = any(item.get("critical") for item in failed) or bool(regressions)
    recommendation = "Retornar ao desenvolvimento" if critical else ("Aprovar com ressalvas" if failed or warnings else "Aprovar")
    return ValidationResult(tuple(asdict(check) for check in checks), tuple(passed), tuple(failed), tuple(warnings), tuple(regressions), tuple(evidence), recommendation)
