#!/usr/bin/env python3
"""Executa e avalia decisões de roteamento do Codex sem mutações externas."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals/routing-cases.json"
SCHEMA_PATH = ROOT / "evals/routing-result.schema.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Executa os casos usando codex exec.")
    parser.add_argument("--case", action="append", dest="case_ids", help="Executa somente o ID informado.")
    parser.add_argument("--model", help="Modelo opcional para o eval ao vivo.")
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high"),
        default="low",
        help="Esforço do modelo no eval ao vivo (padrão: low).",
    )
    return parser.parse_args()


def load_cases(selected: set[str] | None) -> list[dict]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = data["cases"]
    if selected:
        known = {case["id"] for case in cases}
        missing = selected - known
        if missing:
            raise ValueError(f"Casos desconhecidos: {', '.join(sorted(missing))}")
        cases = [case for case in cases if case["id"] in selected]
    return cases


def prompt_for(case: dict) -> str:
    return f"""
Avalie somente o roteamento que o Jarvis Agent SESAB deveria aplicar ao pedido abaixo.
Não chame ferramentas, não consulte serviços externos, não altere arquivos e não implemente a tarefa.
Retorne apenas o JSON solicitado pelo schema, indicando as skills e os agentes especializados que
deveriam ser usados, se a tarefa exige confirmação imediatamente antes de uma mutação, se é somente
leitura e quais invariantes nomeadas são aplicáveis.

Use somente estes identificadores de invariantes quando forem aplicáveis:
- create-on-not-rn: no AGHUse, sem RN compatível, a nova classe de negócio deve ser ON.
- idempotent-apply-and-rollback: aplicação e rollback de banco devem ser idempotentes.

Em requires_confirmation, marque true somente quando for necessária uma nova confirmação
imediatamente antes de escrita externa ou compartilhada, como Redmine, banco ou deploy.
Edição de arquivos já autorizada por um pedido de implementação não exige nova confirmação.

Pedido a classificar:
{case["prompt"]}
""".strip()


def run_live(case: dict, model: str | None, reasoning_effort: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="jarvis-agent-eval-") as temp_dir:
        output = Path(temp_dir) / "result.json"
        command = [
            "codex",
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--config",
            f'model_reasoning_effort="{reasoning_effort}"',
            "--output-schema",
            str(SCHEMA_PATH),
            "--output-last-message",
            str(output),
            "--cd",
            str(ROOT),
        ]
        if model:
            command.extend(["--model", model])
        command.append(prompt_for(case))
        result = subprocess.run(command, text=True)
        if result.returncode:
            raise RuntimeError(f"codex exec falhou com código {result.returncode}")
        return json.loads(output.read_text(encoding="utf-8"))


def compare(case: dict, actual: dict) -> list[str]:
    errors: list[str] = []
    expected_skills = set(case.get("expected_skills", []))
    actual_skills = {
        skill.rsplit(":", 1)[-1]
        for skill in actual.get("skills", [])
        if isinstance(skill, str)
    }
    if expected_skills != actual_skills:
        errors.append(f"skills: esperado={sorted(expected_skills)}, obtido={sorted(actual_skills)}")

    expected_agents = set(case.get("expected_agents", []))
    actual_agents = set(actual.get("agents", []))
    if not expected_agents.issubset(actual_agents):
        errors.append(f"agents ausentes: {sorted(expected_agents - actual_agents)}")
    forbidden = set(case.get("forbidden_agents", [])) & actual_agents
    if forbidden:
        errors.append(f"agents proibidos: {sorted(forbidden)}")

    for field in ("requires_confirmation", "read_only"):
        if actual.get(field) is not case.get(field):
            errors.append(f"{field}: esperado={case.get(field)}, obtido={actual.get(field)}")

    expected_invariants = set(case.get("invariants", []))
    actual_invariants = set(actual.get("invariants", []))
    if not expected_invariants.issubset(actual_invariants):
        errors.append(f"invariantes ausentes: {sorted(expected_invariants - actual_invariants)}")
    return errors


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(set(args.case_ids) if args.case_ids else None)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    if not args.live:
        print(f"OK: {len(cases)} caso(s) carregado(s). Use --live para avaliar com codex exec.")
        return 0

    failures = 0
    for case in cases:
        print(f"AVALIANDO: {case['id']}", flush=True)
        try:
            actual = run_live(case, args.model, args.reasoning_effort)
            errors = compare(case, actual)
        except (OSError, RuntimeError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
        if errors:
            failures += 1
            for error in errors:
                print(f"FALHA {case['id']}: {error}")
        else:
            print(f"OK: {case['id']}")
    print(f"Resumo: {len(cases) - failures} aprovado(s), {failures} reprovado(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
