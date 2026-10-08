"""Canonical AGHUse Assistant application entrypoint."""
from __future__ import annotations

import argparse
import json
import re
import sys
from .api.runs import RunService

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?")
    parser.add_argument("--project-id", default="aghuse")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", action="store_true")
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
        objective_text = objective.strip()
        payload = {"project": args.project_id, "operation": operation, "objective": objective_text}
        if operation == "ANALYZE" and re.fullmatch(r"#?\d+", objective_text):
            task_ref = objective_text.lstrip("#")
            payload.update({"task_ref": task_ref, "objective": f"Analisar tecnicamente o contexto do projeto associado à tarefa Redmine #{task_ref}"})
        if operation in {"IMPLEMENT", "MANUTENCAO"} and args.execute and not args.confirm:
            print(json.dumps({"status": "WAITING_INPUT", "message": f"{operation} exige --confirm explícito."}, ensure_ascii=False))
            return 0
        service = RunService()
        run = service.create(payload)
        if args.execute:
            result = service.execute(run["run_id"])
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else service.present_result(result))
        else:
            print(json.dumps(run, ensure_ascii=False, indent=2))
        return 0
    else:
        parser.error("use /analisar, /planejar, /implementar, /validar ou /manutencao")

__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
