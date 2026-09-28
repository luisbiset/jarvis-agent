#!/usr/bin/env python3
"""Executa, reproduz e pontua decisões de roteamento do Jarvis sem mutações externas."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals/routing-cases.json"
SCHEMA_PATH = ROOT / "evals/routing-result.schema.json"
DEFAULT_BASELINE = ROOT / "evals/baselines/routing-v2.json"
SCORE_NAMES = ("routing_accuracy", "over_routing", "under_routing", "stage_order", "confirmation_safety")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--live", action="store_true", help="Executa os casos usando codex exec.")
    source.add_argument("--result-dir", type=Path, help="Reproduz resultados <case-id>.json já capturados.")
    parser.add_argument("--case", action="append", dest="case_ids", help="Executa somente o ID informado.")
    parser.add_argument("--canary", action="store_true", help="Executa somente o subconjunto crítico marcado como canary.")
    parser.add_argument("--model", help="Modelo opcional para o eval ao vivo.")
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high"),
        default="low",
        help="Esforço do modelo no eval ao vivo (padrão: low).",
    )
    parser.add_argument("--save-results", type=Path, help="Grava respostas ao vivo para replay posterior.")
    parser.add_argument("--json-report", type=Path, help="Grava scorecard e falhas em JSON.")
    parser.add_argument("--compare-baseline", action="store_true", help="Compara scorecard com o baseline V2.")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--write-baseline", type=Path, help="Grava um baseline com o scorecard obtido.")
    return parser.parse_args()


def load_cases(selected: set[str] | None, canary: bool = False) -> list[dict[str, Any]]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 2:
        raise ValueError("routing-cases.json deve usar schema_version 2")
    cases = data["cases"]
    if selected:
        known = {case["id"] for case in cases}
        missing = selected - known
        if missing:
            raise ValueError(f"Casos desconhecidos: {', '.join(sorted(missing))}")
        cases = [case for case in cases if case["id"] in selected]
    if canary:
        cases = [case for case in cases if case.get("canary") is True]
    if not cases:
        raise ValueError("nenhum caso selecionado")
    return cases


def prompt_for(case: dict[str, Any]) -> str:
    return f"""
Avalie somente o roteamento que o Jarvis Agent SESAB deveria aplicar ao pedido abaixo.
Não chame ferramentas, não consulte serviços externos, não altere arquivos e não implemente a tarefa.
Retorne apenas o JSON solicitado pelo schema.

Classifique antes de rotear:
- TRIVIAL: um especialista, auditor opcional, máximo 1 agente.
- LOCALIZED: até 3 agentes, QA ou auditor conforme risco.
- TRANSVERSAL: discovery, developer, QA e auditor, máximo 6 agentes.
- CRITICAL: transversal, reviewer e gate humano reforçado, máximo 8 agentes.

Use operational_mode COPILOT para proposta com intervenção humana, ASSISTED_AUTOPILOT para edição
já autorizada no repositório e READ_ONLY_AUDIT quando qualquer write estiver proibido. Use FAST para
busca/roteamento mecânico, NORMAL para implementação localizada e DEEP só para ambiguidade, risco
alto, investigação difícil ou revisão sistêmica. Não chame agentes extras "por garantia".

Em stages, registre a ordem operacional. Use parallel apenas quando as frentes forem independentes.
Se a resposta correta for parar antes da implementação, deixe os estágios posteriores ausentes e
preencha stop_reason. requires_confirmation é true somente para confirmação imediatamente anterior
a escrita externa/compartilhada; edição local já autorizada não exige nova confirmação.

Invariantes disponíveis:
- create-on-not-rn: política AGH-RN-001.
- idempotent-apply-and-rollback: política AGH-DB-002.
- aghuse-db-scripts-outside-git: política AGH-DB-001.
- human-gate: política FLOW-001.
- explicit-external-authorization: política FLOW-002.

Pedido a classificar:
{case["prompt"]}
""".strip()


def run_live(case: dict[str, Any], model: str | None, reasoning_effort: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="jarvis-agent-eval-") as temp_dir:
        output = Path(temp_dir) / "result.json"
        command = [
            "codex", "exec", "--ephemeral", "--sandbox", "read-only",
            "--config", f'model_reasoning_effort="{reasoning_effort}"',
            "--output-schema", str(SCHEMA_PATH), "--output-last-message", str(output), "--cd", str(ROOT),
        ]
        if model:
            command.extend(["--model", model])
        command.append(prompt_for(case))
        result = subprocess.run(command, text=True)
        if result.returncode:
            raise RuntimeError(f"codex exec falhou com código {result.returncode}")
        return json.loads(output.read_text(encoding="utf-8"))


def normalized_skills(actual: dict[str, Any]) -> set[str]:
    return {skill.rsplit(":", 1)[-1] for skill in actual.get("skills", []) if isinstance(skill, str)}


def normalized_stages(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for stage in stages:
        agents = list(stage.get("agents", []))
        if stage.get("mode") == "parallel":
            agents.sort()
        normalized.append({"mode": stage.get("mode"), "agents": agents})
    return normalized


def compare(case: dict[str, Any], actual: dict[str, Any]) -> tuple[list[str], dict[str, bool]]:
    errors: list[str] = []
    expected_skills = set(case.get("expected_skills", []))
    actual_skills = normalized_skills(actual)
    expected_agents = set(case.get("expected_agents", []))
    allowed_agents = expected_agents | set(case.get("allowed_agents", []))
    actual_agents = set(actual.get("agents", []))
    missing_agents = expected_agents - actual_agents
    extra_agents = actual_agents - allowed_agents
    forbidden_agents = set(case.get("forbidden_agents", [])) & actual_agents

    routing_ok = expected_skills == actual_skills
    if not routing_ok:
        errors.append(f"skills: esperado={sorted(expected_skills)}, obtido={sorted(actual_skills)}")
    if missing_agents:
        errors.append(f"agents ausentes: {sorted(missing_agents)}")
    if extra_agents:
        errors.append(f"over-routing: agents extras={sorted(extra_agents)}")
    if forbidden_agents:
        errors.append(f"agents proibidos: {sorted(forbidden_agents)}")

    max_agents = case["max_agents"]
    budget_ok = len(actual_agents) <= max_agents and actual.get("max_agents") == max_agents
    if len(actual_agents) > max_agents:
        errors.append(f"budget: {len(actual_agents)} agentes usados, máximo {max_agents}")
    if actual.get("max_agents") != max_agents:
        errors.append(f"max_agents: esperado={max_agents}, obtido={actual.get('max_agents')}")
    if actual.get("max_parallel_agents") != case["max_parallel_agents"]:
        errors.append(
            f"max_parallel_agents: esperado={case['max_parallel_agents']}, obtido={actual.get('max_parallel_agents')}"
        )
        budget_ok = False

    expected_stages = normalized_stages(case.get("expected_stages", []))
    actual_stages = normalized_stages(actual.get("stages", []))
    stages_ok = expected_stages == actual_stages
    if not stages_ok:
        errors.append(f"stages: esperado={expected_stages}, obtido={actual_stages}")
    largest_parallel = max(
        (len(stage["agents"]) for stage in actual_stages if stage["mode"] == "parallel"), default=0
    )
    if largest_parallel > case["max_parallel_agents"]:
        stages_ok = False
        errors.append(f"paralelismo real {largest_parallel} excede {case['max_parallel_agents']}")

    classifications_ok = True
    for field in ("complexity", "risk_class", "operational_mode", "reasoning_class", "stop_reason"):
        if actual.get(field) != case.get(field):
            classifications_ok = False
            errors.append(f"{field}: esperado={case.get(field)!r}, obtido={actual.get(field)!r}")

    confirmation_ok = True
    for field in ("requires_confirmation", "read_only"):
        if actual.get(field) is not case.get(field):
            confirmation_ok = False
            errors.append(f"{field}: esperado={case.get(field)}, obtido={actual.get(field)}")

    expected_invariants = set(case.get("invariants", []))
    actual_invariants = set(actual.get("invariants", []))
    if expected_invariants != actual_invariants:
        routing_ok = False
        errors.append(f"invariants: esperado={sorted(expected_invariants)}, obtido={sorted(actual_invariants)}")

    scores = {
        "routing_accuracy": routing_ok and classifications_ok,
        "over_routing": not extra_agents and not forbidden_agents and budget_ok,
        "under_routing": not missing_agents,
        "stage_order": stages_ok,
        "confirmation_safety": confirmation_ok,
    }
    return errors, scores


def behavior_hash() -> str:
    digest = hashlib.sha256()
    paths = [CASES_PATH, SCHEMA_PATH, ROOT / "contracts/version.json"]
    paths.extend(sorted((ROOT / "agents").glob("*.toml")))
    paths.extend(sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md")))
    for path in paths:
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def scorecard(case_scores: list[dict[str, bool]]) -> dict[str, float]:
    total = len(case_scores)
    return {
        name: round(100 * sum(item[name] for item in case_scores) / total, 2) if total else 0.0
        for name in SCORE_NAMES
    }


def baseline_payload(report: dict[str, Any]) -> dict[str, Any]:
    version = json.loads((ROOT / "contracts/version.json").read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "jarvis_version": version["jarvis_version"],
        "behavior_hash": behavior_hash(),
        "minimum_scores": report["scorecard"],
        "case_ids": report["case_ids"],
    }


def compare_baseline(report: dict[str, Any], path: Path) -> list[str]:
    baseline = json.loads(path.read_text(encoding="utf-8"))
    failures = []
    for name, minimum in baseline.get("minimum_scores", {}).items():
        actual = report["scorecard"].get(name, 0)
        if actual < minimum:
            failures.append(f"baseline {name}: mínimo={minimum}, obtido={actual}")
    return failures


def main() -> int:
    args = parse_args()
    try:
        cases = load_cases(set(args.case_ids) if args.case_ids else None, args.canary)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2

    if not args.live and not args.result_dir:
        print(
            f"OK: {len(cases)} caso(s) V2 carregado(s). Use --live para avaliar ou --result-dir para replay."
        )
        return 0

    failures: list[dict[str, Any]] = []
    all_scores: list[dict[str, bool]] = []
    if args.save_results:
        args.save_results.mkdir(parents=True, exist_ok=True)

    for case in cases:
        print(f"AVALIANDO: {case['id']}", flush=True)
        try:
            if args.live:
                actual = run_live(case, args.model, args.reasoning_effort)
                if args.save_results:
                    destination = args.save_results / f"{case['id']}.json"
                    destination.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                actual = json.loads((args.result_dir / f"{case['id']}.json").read_text(encoding="utf-8"))
            errors, scores = compare(case, actual)
        except (OSError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
            errors = [str(exc)]
            scores = {name: False for name in SCORE_NAMES}
        all_scores.append(scores)
        if errors:
            failures.append({"case_id": case["id"], "errors": errors, "scores": scores})
            for error in errors:
                print(f"FALHA {case['id']}: {error}")
        else:
            print(f"OK: {case['id']}")

    report = {
        "schema_version": 2,
        "behavior_hash": behavior_hash(),
        "case_ids": [case["id"] for case in cases],
        "passed": len(cases) - len(failures),
        "failed": len(failures),
        "scorecard": scorecard(all_scores),
        "failures": failures,
    }
    baseline_errors: list[str] = []
    if args.compare_baseline:
        try:
            baseline_errors = compare_baseline(report, args.baseline)
        except (OSError, KeyError, json.JSONDecodeError) as exc:
            baseline_errors = [f"não foi possível ler baseline: {exc}"]
        report["baseline_errors"] = baseline_errors
        for error in baseline_errors:
            print(f"FALHA BASELINE: {error}")
    if args.write_baseline:
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(
            json.dumps(baseline_payload(report), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Scorecard: {json.dumps(report['scorecard'], ensure_ascii=False, sort_keys=True)}")
    print(f"Resumo: {report['passed']} aprovado(s), {report['failed']} reprovado(s).")
    return 1 if failures or baseline_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
