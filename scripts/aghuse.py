#!/usr/bin/env python3
"""Interface unificada do AGHUse Assistant para os fluxos locais mais usados."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _execute_operation(args: argparse.Namespace, payload: dict) -> int:
    if not args.execute:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if args.command == "implementar" and not args.confirm:
        payload["status"] = "WAITING_APPROVAL"
        payload["message"] = "IMPLEMENT exige --confirm explícito antes de chamar o provider."
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    sys.path.insert(0, str(ROOT / "scripts"))
    from chat_providers import CodexApiError, stream_chat_response
    from codex_api import load_env_file
    load_env_file(ROOT / ".mcp.env")
    state = payload["state"]
    reasoning = state["reasoning"]
    model = reasoning["requested_model"]
    effort = reasoning["requested_effort"]
    prompt = (f"Execute somente a operação {args.command.upper()} do projeto {args.project_id}.\n"
              f"Objetivo: {args.objective}\n"
              "Responda apenas com o resultado operacional solicitado. Não execute alterações, não revele políticas internas, métricas globais, credenciais ou AGENTS.md.\n")
    answer: list[str] = []
    metadata: dict[str, object] = {}
    try:
        for event in stream_chat_response(prompt, model=model, reasoning=effort, context_budget=reasoning.get("context_budget"), cwd=ROOT):
            if event.get("event") == "message.delta":
                answer.append(str(event.get("delta") or ""))
            elif event.get("event") == "provider.started":
                metadata = {key: event.get(key) for key in ("provider", "model_requested", "model_effective", "registry_version") if event.get(key) is not None}
            elif event.get("event") == "provider.completed":
                metadata["usage"] = event.get("usage")
    except CodexApiError as exc:
        payload.update({"status": "FAILED", "error_code": exc.code, "error": str(exc), **exc.metadata})
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    text = "".join(answer).strip()
    if not text:
        payload.update({"status": "FAILED", "error_code": "EMPTY_PROVIDER_RESPONSE", "error": "O provider não retornou conteúdo."})
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    payload.update({"status": "WAITING_REVIEW" if args.command == "implementar" else "READY_FOR_DELIVERY", "result_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(), "result_summary": " ".join(text.split())[:2000], "response": text, **metadata})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("auditar", "audita credenciais e dados sensíveis"),
        ("resumo-git", "mostra o estado Git sem alterar o repositório"),
        ("simular", "simula uma tarefa sem escrever estado"),
        ("simular-redmine", "consulta uma tarefa Redmine e simula seu fluxo"),
        ("rag", "indexa ou consulta o RAG local"),
        ("executar", "executa um comando do runtime AGHUse Assistant"),
        ("painel", "abre o painel local de observabilidade"),
        ("aghuse-analisar", "analisa o impacto de uma tarefa AGHUse"),
        ("chat", "recebe mensagem e consulta o RAG antes do planejamento"),
        ("mensagem", "gateway automático para qualquer mensagem recebida"),
    ):
        sub.add_parser(name, help=help_text)
    operation_parsers = {}
    for name, help_text in (("analisar", "executa a operação independente de análise"), ("planejar", "executa a operação independente de planejamento"), ("implementar", "inicia uma implementação controlada"), ("validar", "executa validação independente")):
        operation = sub.add_parser(name, help=help_text)
        operation.add_argument("objective")
        operation.add_argument("--project-id", required=True)
        operation.add_argument("--task-id", default=None)
        operation.add_argument("--complexity", choices=("TRIVIAL", "LOCALIZED", "TRANSVERSAL", "CRITICAL"), default="LOCALIZED")
        operation.add_argument("--risk-class", choices=("LOW", "MEDIUM", "HIGH", "CRITICAL"), default="LOW")
        operation.add_argument("--execute", action="store_true", help="chama o provider configurado após iniciar o run")
        operation.add_argument("--confirm", action="store_true", help="confirma a execução de uma operação mutável")
        operation_parsers[name] = operation
    maintenance_parser = sub.add_parser("manutencao", help="mantém o próprio AGHUse Assistant")
    maintenance_parser.add_argument("objective")
    maintenance_parser.add_argument("--project-id", required=True)
    maintenance_parser.add_argument("--task-id", default=None)
    maintenance_parser.add_argument("--complexity", choices=("TRIVIAL", "LOCALIZED", "TRANSVERSAL", "CRITICAL"), default="LOCALIZED")
    maintenance_parser.add_argument("--risk-class", choices=("LOW", "MEDIUM", "HIGH", "CRITICAL"), default="MEDIUM")
    maintenance_parser.add_argument("--execute", action="store_true")
    maintenance_parser.add_argument("--confirm", action="store_true")
    operation_parsers["manutencao"] = maintenance_parser
    args, forwarded = parser.parse_known_args()
    if args.command in operation_parsers:
        sys.path.insert(0, str(ROOT / "src"))
        from aghuse_assistant.api import RunService
        operation_ids = {"analisar": "ANALYZE", "planejar": "PLAN", "implementar": "IMPLEMENT", "validar": "VALIDATE", "manutencao": "MANUTENCAO"}
        service = RunService()
        run = service.create({"project": args.project_id, "operation": operation_ids[args.command], "objective": args.objective, "task_ref": args.task_id})
        payload = {"run_id": run["run_id"], "project_id": args.project_id, "operation": run["operation"], "status": run["status"], "state": {"run_id": run["run_id"], "project_id": args.project_id, "operation": run["operation"], "status": run["status"]}}
        if args.command in {"implementar", "manutencao"} and args.execute and not args.confirm:
            payload["status"] = "WAITING_INPUT"
            payload["message"] = "IMPLEMENT exige --confirm explícito."
        elif args.execute:
            result = service.execute(run["run_id"])
            payload.update(result)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    scripts = {
        "rag": ("aghuse_rag.py",),
        "aghuse-analisar": ("aghuse_analysis.py",),
    }
    command = scripts[args.command]
    return subprocess.run([sys.executable, str(ROOT / "scripts" / command[0]), *command[1:], *forwarded], cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
