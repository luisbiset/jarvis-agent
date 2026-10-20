"""Canonical AGHUse Assistant application entrypoint."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .gateway import ToolGateway, register_local_analysis_tools
from .operations.analyze import execute_artifact
from .orchestrator import Orchestrator
from .orchestrator.models import ExecutionResult, ExecutionState

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?")
    parser.add_argument("--project-id", default="aghuse")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--plan", action="store_true", help="encadeia planejamento após uma análise completa")
    parser.add_argument("--json", action="store_true", help="retorna o envelope interno validado")
    args, unknown = parser.parse_known_args()
    message = " ".join([part for part in (args.message, *unknown) if part]) or sys.stdin.read().strip()
    if not message:
        parser.error("informe uma mensagem")
    command_name, _, objective = message.partition(" ")
    operations = {"/analisar": "ANALYZE", "/planejar": "PLAN", "/implementar": "IMPLEMENT", "/validar": "VALIDATE", "/manutencao": "MANUTENCAO", "/manutenção": "MANUTENCAO"}
    if command_name.lower() in operations:
        if not objective.strip():
            parser.error(f"informe o objetivo após {command_name}")
        operation = operations[command_name.lower()]
        if args.plan and operation != "ANALYZE":
            parser.error("--plan é válido somente com /analisar")
        objective_text = objective.strip()
        payload = {"project": args.project_id, "operation": operation, "objective": objective_text}
        if operation == "ANALYZE" and re.fullmatch(r"#?\d+", objective_text):
            task_ref = objective_text.lstrip("#")
            payload.update({"task_ref": task_ref, "objective": f"Analisar tecnicamente o contexto do projeto associado à tarefa Redmine #{task_ref}"})
        if operation in {"IMPLEMENT", "MANUTENCAO"} and args.execute and not args.confirm:
            print(json.dumps({"status": "WAITING_INPUT", "message": f"{operation} exige --confirm explícito."}, ensure_ascii=False))
            return 0
        gateway = ToolGateway()
        register_local_analysis_tools(gateway, Path.cwd())
        orchestrator = Orchestrator(gateway=gateway)
        context = orchestrator.create(payload)
        if args.plan:
            artifact = execute_artifact(context, gateway)
            analysis = _analysis_execution(context, artifact)
            planning = _planning_execution(orchestrator, payload, artifact, analysis)
            print(json.dumps(_compound_execution(analysis, planning), ensure_ascii=False, indent=2))
        else:
            result = orchestrator.execute(context, confirm=args.confirm)
            print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
        return 0
    else:
        parser.error("use /analisar, /planejar, /implementar, /validar ou /manutencao")

__all__ = ["main"]


def _analysis_execution(context, artifact):
    from .analysis.result import to_execution
    return to_execution(context, artifact)


def _planning_execution(orchestrator, payload, artifact, analysis: ExecutionResult) -> ExecutionResult:
    if artifact.coverage.status != "COMPLETE":
        return ExecutionResult(
            "PLAN", analysis.project, analysis.execution_id, ExecutionState.WAITING_INPUT,
            "Análise deve estar COMPLETE antes de planejar",
            {"required_artifact": "analysis", "required_status": "COMPLETE", "analysis_status": artifact.coverage.status},
        )
    plan_payload = {**payload, "operation": "PLAN", "artifacts": {"analysis": artifact.to_dict()}}
    return orchestrator.execute(orchestrator.create(plan_payload))


def _compound_execution(analysis: ExecutionResult, planning: ExecutionResult) -> dict:
    return {
        "operation": "ANALYZE_AND_PLAN",
        "project": analysis.project,
        "state": planning.state.value,
        "summary": planning.summary,
        "data": {"analysis": analysis.as_dict(), "planning": planning.as_dict()},
        "warnings": [*analysis.warnings, *planning.warnings],
        "evidence": analysis.evidence,
    }


if __name__ == "__main__":
    raise SystemExit(main())
