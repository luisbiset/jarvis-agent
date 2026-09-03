#!/usr/bin/env python3
"""Validação determinística e sem dependências do projeto Jarvis Agent."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
COMPLEXITIES = {"TRIVIAL", "LOCALIZED", "TRANSVERSAL", "CRITICAL"}
RISKS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
MODES = {"COPILOT", "ASSISTED_AUTOPILOT", "READ_ONLY_AUDIT"}
REASONING_CLASSES = {"FAST", "NORMAL", "DEEP"}
STOP_REASONS = {
    None,
    "AMBIGUOUS_REQUIREMENT",
    "SHARED_CONTRACT_OUT_OF_SCOPE",
    "TEST_CONTRADICTION",
    "EXTERNAL_AUTHORIZATION_REQUIRED",
    "INSUFFICIENT_CONTEXT",
    "VALIDATION_NOT_REPRODUCIBLE",
    "SPECIALIST_DIVERGENCE",
    "NEEDS_EXPLANATION",
}


def fail(message: str) -> None:
    ERRORS.append(message)


def load_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except Exception as exc:
        fail(f"JSON inválido em {path.relative_to(ROOT)}: {exc}")
        return {}


def validate_agents() -> set[str]:
    names: set[str] = set()
    for path in sorted((ROOT / "agents").glob("*.toml")):
        try:
            with path.open("rb") as stream:
                data = tomllib.load(stream)
        except Exception as exc:
            fail(f"TOML inválido em {path.relative_to(ROOT)}: {exc}")
            continue
        for field in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(field), str) or not data[field].strip():
                fail(f"{path.relative_to(ROOT)} não possui {field} válido")
        name = data.get("name")
        if isinstance(name, str):
            if name != path.stem:
                fail(f"Nome {name!r} difere do arquivo {path.name}")
            if name in names:
                fail(f"Agente duplicado: {name}")
            names.add(name)
        effort = data.get("model_reasoning_effort")
        if effort is not None:
            fail(f"{path.relative_to(ROOT)} fixa model_reasoning_effort={effort!r}; a V3 exige policy adaptativa")
    return names


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"Skill sem frontmatter: {path.relative_to(ROOT)}")
        return {}
    try:
        header = text.split("---\n", 2)[1]
    except IndexError:
        fail(f"Frontmatter incompleto: {path.relative_to(ROOT)}")
        return {}
    result: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def validate_plugins() -> set[str]:
    plugin_names: set[str] = set()
    marketplace = load_json(ROOT / ".agents/plugins/marketplace.json")
    entries = marketplace.get("plugins", [])
    market_names = {entry.get("name") for entry in entries if isinstance(entry, dict)}

    for plugin_dir in sorted((ROOT / "plugins").iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / ".codex-plugin/plugin.json"
        if not manifest_path.is_file():
            fail(f"Plugin sem manifest: {plugin_dir.name}")
            continue
        manifest = load_json(manifest_path)
        name = manifest.get("name")
        if name != plugin_dir.name:
            fail(f"Manifest de {plugin_dir.name} declara nome {name!r}")
        if not isinstance(manifest.get("version"), str):
            fail(f"Plugin {plugin_dir.name} sem versão")
        if name in plugin_names:
            fail(f"Plugin duplicado: {name}")
        if isinstance(name, str):
            plugin_names.add(name)
        if plugin_dir.name not in market_names:
            fail(f"Plugin ausente do marketplace: {plugin_dir.name}")
        if "mcpServers" in manifest and not (plugin_dir / ".mcp.json").is_file():
            fail(f"Plugin {plugin_dir.name} referencia .mcp.json inexistente")
        default_prompts = manifest.get("interface", {}).get("defaultPrompt", [])
        if not isinstance(default_prompts, list) or len(default_prompts) > 3:
            fail(f"Plugin {plugin_dir.name} deve possuir no máximo três prompts padrão")

        for skill_dir in sorted((plugin_dir / "skills").glob("*")):
            skill_path = skill_dir / "SKILL.md"
            if not skill_path.is_file():
                fail(f"Skill sem SKILL.md: {skill_dir.relative_to(ROOT)}")
                continue
            frontmatter = parse_frontmatter(skill_path)
            if frontmatter.get("name") != skill_dir.name:
                fail(f"Nome da skill difere da pasta: {skill_dir.relative_to(ROOT)}")
            if not frontmatter.get("description"):
                fail(f"Skill sem description: {skill_dir.relative_to(ROOT)}")
            ui_path = skill_dir / "agents/openai.yaml"
            if ui_path.is_file():
                ui = ui_path.read_text(encoding="utf-8")
                if "default_prompt:" not in ui or f"${skill_dir.name}" not in ui:
                    fail(f"default_prompt deve mencionar ${skill_dir.name}: {ui_path.relative_to(ROOT)}")
    if market_names != plugin_names:
        fail(f"Marketplace e diretórios divergem: marketplace={sorted(market_names)}, plugins={sorted(plugin_names)}")
    return plugin_names


def validate_evals(agent_names: set[str]) -> None:
    data = load_json(ROOT / "evals/routing-cases.json")
    schema = load_json(ROOT / "evals/routing-result.schema.json")
    if data.get("schema_version") != 2:
        fail("Evals de roteamento devem usar schema_version 2")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        fail("Schema do resultado dos evals deve ser um objeto fechado")
    schema_required = {
        "skills", "agents", "stages", "complexity", "risk_class", "operational_mode",
        "reasoning_class", "max_agents", "max_parallel_agents", "stop_reason",
        "requires_confirmation", "read_only", "invariants",
    }
    if set(schema.get("required", [])) != schema_required:
        fail("Schema do resultado dos evals não declara todos os campos V2")
    ids: set[str] = set()
    allowed_invariants = {
        "create-on-not-rn",
        "idempotent-apply-and-rollback",
        "aghuse-db-scripts-outside-git",
        "human-gate",
        "explicit-external-authorization",
    }
    required_fields = {
        "id",
        "prompt",
        "canary",
        "expected_skills",
        "expected_agents",
        "allowed_agents",
        "forbidden_agents",
        "expected_stages",
        "complexity",
        "risk_class",
        "operational_mode",
        "reasoning_class",
        "max_agents",
        "max_parallel_agents",
        "stop_reason",
        "requires_confirmation",
        "read_only",
        "invariants",
    }
    known_skills = {
        path.parent.name
        for path in (ROOT / "plugins").glob("*/skills/*/SKILL.md")
    }
    for case in data.get("cases", []):
        if not isinstance(case, dict):
            fail("Caso de avaliação não é objeto")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            fail("Caso de avaliação sem id")
            continue
        if case_id in ids:
            fail(f"ID de avaliação duplicado: {case_id}")
        ids.add(case_id)
        missing_fields = required_fields - set(case)
        if missing_fields:
            fail(f"Avaliação {case_id} sem campos: {sorted(missing_fields)}")
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            fail(f"Avaliação {case_id} sem prompt")
        for field in ("expected_skills", "expected_agents", "allowed_agents", "forbidden_agents", "expected_stages", "invariants"):
            if field in case and not isinstance(case[field], list):
                fail(f"Avaliação {case_id} possui {field} inválido")
        for field in ("canary", "requires_confirmation", "read_only"):
            if not isinstance(case.get(field), bool):
                fail(f"Avaliação {case_id} possui {field} inválido")
        if case.get("complexity") not in COMPLEXITIES:
            fail(f"Avaliação {case_id} possui complexity inválida")
        if case.get("risk_class") not in RISKS:
            fail(f"Avaliação {case_id} possui risk_class inválida")
        if case.get("operational_mode") not in MODES:
            fail(f"Avaliação {case_id} possui operational_mode inválido")
        if case.get("reasoning_class") not in REASONING_CLASSES:
            fail(f"Avaliação {case_id} possui reasoning_class inválida")
        if case.get("stop_reason") not in STOP_REASONS:
            fail(f"Avaliação {case_id} possui stop_reason inválido")
        max_agents = case.get("max_agents")
        max_parallel = case.get("max_parallel_agents")
        if not isinstance(max_agents, int) or max_agents < 0:
            fail(f"Avaliação {case_id} possui max_agents inválido")
        if not isinstance(max_parallel, int) or max_parallel < 1:
            fail(f"Avaliação {case_id} possui max_parallel_agents inválido")
        for skill in case.get("expected_skills", []):
            if skill not in known_skills:
                fail(f"Avaliação {case_id} referencia skill desconhecida: {skill}")
        referenced_agents = (
            case.get("expected_agents", []) + case.get("allowed_agents", []) + case.get("forbidden_agents", [])
        )
        for agent in referenced_agents:
            if agent not in agent_names:
                fail(f"Avaliação {case_id} referencia agente desconhecido: {agent}")
        overlap = (set(case.get("expected_agents", [])) | set(case.get("allowed_agents", []))) & set(
            case.get("forbidden_agents", [])
        )
        if overlap:
            fail(f"Avaliação {case_id} exige e proíbe os mesmos agentes: {sorted(overlap)}")
        stage_agents: list[str] = []
        largest_parallel = 0
        for index, stage in enumerate(case.get("expected_stages", [])):
            if not isinstance(stage, dict) or set(stage) != {"mode", "agents"}:
                fail(f"Avaliação {case_id} possui estágio {index} inválido")
                continue
            if stage.get("mode") not in {"parallel", "sequential"} or not isinstance(stage.get("agents"), list):
                fail(f"Avaliação {case_id} possui estágio {index} malformado")
                continue
            if stage["mode"] == "sequential" and len(stage["agents"]) != 1:
                fail(f"Avaliação {case_id} possui estágio sequencial com quantidade diferente de 1")
            if stage["mode"] == "parallel":
                largest_parallel = max(largest_parallel, len(stage["agents"]))
            stage_agents.extend(stage["agents"])
            for agent in stage["agents"]:
                if agent not in agent_names:
                    fail(f"Avaliação {case_id} possui agente desconhecido no estágio: {agent}")
        if set(stage_agents) != set(case.get("expected_agents", [])):
            fail(f"Avaliação {case_id} diverge entre expected_agents e expected_stages")
        if isinstance(max_agents, int) and len(set(case.get("expected_agents", []))) > max_agents:
            fail(f"Avaliação {case_id} exige mais agentes que max_agents")
        if isinstance(max_parallel, int) and largest_parallel > max_parallel:
            fail(f"Avaliação {case_id} excede max_parallel_agents nos estágios")
        unknown_invariants = set(case.get("invariants", [])) - allowed_invariants
        if unknown_invariants:
            fail(f"Avaliação {case_id} possui invariantes desconhecidas: {sorted(unknown_invariants)}")


def validate_versioned_contracts(agent_names: set[str]) -> None:
    contract_dir = ROOT / "contracts"
    required = {
        "version.json",
        "reasoning-policy.json",
        "knowledge-transfer-policy.json",
        "policy-registry.json",
        "handoff.schema.json",
        "technical-handoff.schema.json",
        "execution-state.schema.json",
        "role-boundaries.json",
        "task-patterns.json",
        "protocol.md",
        "CHANGELOG.md",
    }
    missing = [name for name in sorted(required) if not (contract_dir / name).is_file()]
    if missing:
        fail(f"Contratos versionados ausentes: {missing}")
        return

    version = load_json(contract_dir / "version.json")
    if version.get("jarvis_version") != "3.1.0" or version.get("execution_state_schema_version") != "3.1.0" or version.get("telemetry_schema_version") != "3.1.0" or version.get("reasoning_policy_version") != "3.1.0" or version.get("technical_handoff_schema_version") != "1.0.0" or version.get("knowledge_transfer_policy_version") != "1.0.0" or version.get("routing_schema_version") != 2:
        fail("contracts/version.json não declara Jarvis/runtime/policy 3.1.0 e routing schema 2")

    handoff = load_json(contract_dir / "handoff.schema.json")
    handoff_required = {
        "schema_version", "run_id", "jarvis_version", "status", "stage", "complexity",
        "risk_class", "operational_mode", "reasoning_class", "requirement_ids", "files",
        "contracts_changed", "decisions", "validations", "risks", "limitations", "blockers",
        "stop_reason", "ownership", "next",
    }
    if set(handoff.get("required", [])) != handoff_required or handoff.get("additionalProperties") is not False:
        fail("handoff.schema.json não é o contrato fechado V2 esperado")
    validations = handoff.get("properties", {}).get("validations", {}).get("required", [])
    if set(validations) != {"executed", "passed", "failed", "not_executed"}:
        fail("handoff V2 deve explicitar validações não executadas")

    execution = load_json(contract_dir / "execution-state.schema.json")
    if execution.get("additionalProperties") is not False:
        fail("execution-state.schema.json deve ser fechado")

    policies = load_json(contract_dir / "policy-registry.json").get("policies", [])
    policy_ids: set[str] = set()
    for policy in policies:
        policy_id = policy.get("id")
        if not isinstance(policy_id, str) or not re.fullmatch(r"[A-Z]+(?:-[A-Z]+)?-\d{3}", policy_id):
            fail(f"Policy ID inválido: {policy_id!r}")
            continue
        if policy_id in policy_ids:
            fail(f"Policy ID duplicado: {policy_id}")
        policy_ids.add(policy_id)
        references = policy.get("enforced_by", [])
        existing_texts = []
        for relative in references:
            path = ROOT / relative
            if not path.is_file():
                fail(f"Policy {policy_id} referencia arquivo ausente: {relative}")
            else:
                existing_texts.append(path.read_text(encoding="utf-8"))
        if existing_texts and not any(policy_id in text for text in existing_texts):
            fail(f"Policy {policy_id} não é citada por nenhum enforcement declarado")

    boundaries = load_json(contract_dir / "role-boundaries.json").get("roles", {})
    expected_roles = {"aghuse_auditor_do_diff", "aghuse_qa", "sesab_reviewer", "qa_homologacao"}
    if set(boundaries) != expected_roles:
        fail("role-boundaries.json não declara as quatro fronteiras de validação")
    evidence_domains = [value.get("primary_evidence") for value in boundaries.values()]
    if len(set(evidence_domains)) != len(evidence_domains):
        fail("Perfis de validação possuem evidência principal duplicada")

    patterns = load_json(contract_dir / "task-patterns.json").get("patterns", [])
    pattern_ids: set[str] = set()
    for pattern in patterns:
        pattern_id = pattern.get("id")
        if not isinstance(pattern_id, str) or pattern_id in pattern_ids:
            fail(f"Padrão de tarefa inválido ou duplicado: {pattern_id!r}")
        pattern_ids.add(pattern_id)
        if pattern.get("complexity") not in COMPLEXITIES or pattern.get("risk_class") not in RISKS:
            fail(f"Padrão {pattern_id} possui classificação inválida")
        agents = pattern.get("agents", [])
        if any(agent not in agent_names for agent in agents):
            fail(f"Padrão {pattern_id} referencia agente desconhecido")
        if not isinstance(pattern.get("max_agents"), int) or len(set(agents)) > pattern["max_agents"]:
            fail(f"Padrão {pattern_id} excede o próprio budget")


def validate_redmine_server() -> None:
    plugin = ROOT / "plugins/redmine-agent"
    modules = sorted((plugin / "src").glob("*.mjs"))
    tests = sorted((plugin / "tests").glob("*.test.mjs"))
    server = plugin / "scripts/server.mjs"
    if not modules or not tests:
        fail("MCP Redmine deve possuir módulos em src/ e testes em tests/")
    for path in [server, *modules, *tests]:
        result = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
        if result.returncode:
            fail(f"JavaScript inválido em {path.relative_to(ROOT)}: {result.stderr.strip()}")

    offline_tests = [plugin / "tests/tools.test.mjs", plugin / "tests/protocol.test.mjs"]
    result = subprocess.run(
        ["node", "--test", *(str(path) for path in offline_tests)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        details = (result.stdout + result.stderr).strip()
        fail(f"Testes offline do MCP Redmine falharam: {details}")


def validate_aghuse_automation() -> None:
    plugin = ROOT / "plugins/aghuse-agent"
    script = plugin / "scripts/aghuse_automacao.py"
    tests = plugin / "tests"
    if not script.is_file():
        fail("Plugin AGHUse deve possuir scripts/aghuse_automacao.py")
        return
    try:
        ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
    except SyntaxError as exc:
        fail(f"Automação AGHUse possui Python inválido: {exc}")
        return
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(tests), "-p", "test_*.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        details = (result.stdout + result.stderr).strip()
        fail(f"Testes das automações AGHUse falharam: {details}")


def validate_jarvis_runtime() -> None:
    scripts = [ROOT / "scripts/jarvis_runtime.py", ROOT / "scripts/run_evals.py", ROOT / "scripts/generate_topology.py"]
    for script in scripts:
        if not script.is_file():
            fail(f"Script V3 ausente: {script.relative_to(ROOT)}")
            continue
        try:
            ast.parse(script.read_text(encoding="utf-8"), filename=str(script))
        except SyntaxError as exc:
            fail(f"Script V3 possui Python inválido em {script.relative_to(ROOT)}: {exc}")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_*.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        details = (result.stdout + result.stderr).strip()
        fail(f"Testes do runtime Jarvis V3 falharam: {details}")
    evals = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_evals.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if evals.returncode:
        fail(f"Carregamento dos evals falhou: {(evals.stdout + evals.stderr).strip()}")
    topology = subprocess.run(
        [sys.executable, str(ROOT / "scripts/generate_topology.py"), "--check"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if topology.returncode:
        fail(f"Topologia gerada está desatualizada: {(topology.stdout + topology.stderr).strip()}")


def validate_reasoning_policy() -> None:
    policy = load_json(ROOT / "contracts/reasoning-policy.json")
    if policy.get("policy_version") != "3.1.0":
        fail("Reasoning policy deve declarar policy_version 3.1.0")
    if policy.get("default_level") != "MEDIUM":
        fail("Reasoning policy deve usar fallback MEDIUM")
    thresholds = policy.get("thresholds", {})
    if thresholds.get("instant_max_score") != 3 or thresholds.get("medium_max_score") != 8:
        fail("Thresholds V3 devem ser INSTANT até 3 e MEDIUM até 8")
    escalation = policy.get("escalation", {})
    if escalation.get("allowed_from") != "MEDIUM" or escalation.get("target") != "HIGH" or escalation.get("max_per_task") != 1:
        fail("Escalada V3 deve permitir somente MEDIUM -> HIGH uma vez")
    budget = policy.get("budget", {})
    if budget.get("max_attempts") != 3 or budget.get("max_total_retries") != 3 or budget.get("max_child_executions") != 3 or budget.get("max_child_depth") != 3:
        fail("Budgets V3 devem limitar tentativas, retries, child executions e child depth a 3")
    expected_routing = {
        "INSTANT": ("gpt-5.6-luna", "low", "SMALL"),
        "MEDIUM": ("gpt-5.6-terra", "medium", "MEDIUM"),
        "HIGH": ("gpt-5.6-sol", "high", "LARGE"),
    }
    for level, expected in expected_routing.items():
        config = policy.get("levels", {}).get(level, {})
        if (config.get("model"), config.get("reasoning_effort"), config.get("context_budget")) != expected:
            fail(f"Roteamento adaptativo inválido para {level}")
    if budget.get("hard_max_model_calls", 0) < 1 or budget.get("max_duration_ms", 0) < 1:
        fail("Budget V3 deve limitar chamadas de modelo e duração")
    if policy.get("model_call_limits") != {"TRIVIAL": 1, "LOCALIZED": 3, "TRANSVERSAL": 5, "CRITICAL": 6}:
        fail("Limites de model calls por complexidade inválidos")
    context_limits = policy.get("context_limits", {})
    for key in ("max_files", "max_context_tokens", "max_tool_reads", "max_raw_bytes"):
        values = [context_limits.get(level, {}).get(key, 0) for level in ("SMALL", "MEDIUM", "LARGE")]
        if any(value <= 0 for value in values) or values != sorted(values):
            fail(f"Context limits inválidos ou não monotônicos para {key}")
    cost_limits = policy.get("cost_limits", {})
    if cost_limits.get("mode") != "OBSERVE_ONLY" or not 0 < cost_limits.get("soft_limit_ratio", 0) < 1:
        fail("Cost limits devem iniciar em OBSERVE_ONLY")


def validate_knowledge_transfer_policy() -> None:
    policy = load_json(ROOT / "contracts/knowledge-transfer-policy.json")
    if policy.get("policy_id") != "FLOW-004" or policy.get("policy_version") != "1.0.0":
        fail("Knowledge transfer deve declarar FLOW-004 e policy_version 1.0.0")
    expected = {
        "TRIVIAL": (False, "NONE", 0, False),
        "LOCALIZED": (True, "SHORT", 0, False),
        "BUSINESS_RULE": (True, "FULL", 3, False),
        "TRANSVERSAL": (True, "FULL", 4, False),
        "CRITICAL": (True, "FULL", 5, True),
    }
    levels = policy.get("levels", {})
    for name, values in expected.items():
        config = levels.get(name, {})
        observed = (config.get("enabled"), config.get("handoff"), config.get("teach_back_questions"), config.get("teach_back_required"))
        if observed != values:
            fail(f"Knowledge transfer inválida para {name}: {observed}")
    budget = policy.get("budget", {})
    if budget.get("max_handoff_tokens") != 4000 or budget.get("max_teachback_turns") != 6:
        fail("Budgets de knowledge transfer devem ser 4000 tokens e 6 turnos")
    schema = load_json(ROOT / "contracts/technical-handoff.schema.json")
    if schema.get("additionalProperties") is not False or schema.get("$id") != "jarvis://contracts/technical-handoff/1.0.0":
        fail("technical-handoff.schema.json deve ser fechado e versionado em 1.0.0")


def validate_critical_contracts() -> None:
    contracts = {
        "config/AGENTS.md": [
            "Aplicar `FLOW-003` a toda tarefa solicitada",
            "não escolher reasoning manualmente quando o policy engine V3 estiver disponível",
            "Antes de executar qualquer trabalho substantivo ou chamar ferramentas, mostrar ao usuário uma linha curta",
            "modelo LLM <model retornado pela policy>",
            "modelo LLM pendente da policy",
            "Somente `MEDIUM` pode escalar automaticamente uma vez para `HIGH`",
            "Registrar tokens e créditos somente quando forem valores observados",
            "Encerrar toda resposta final com uma linha curta",
        ],
        "AGENTS.md": [
            "Aplique `FLOW-003` a toda tarefa",
            "informe as pré-métricas ao usuário antes do trabalho substantivo",
        ],
        "contracts/protocol.md": [
            "Toda tarefa solicitada, inclusive consulta, explicação, diagnóstico somente leitura ou ação externa",
            "Aplicar `FLOW-003`",
            "o fechamento deve dizer `não informados`",
            "`HIGH` nunca escala novamente",
            "O reasoning do agente principal já iniciado não muda no meio da mesma chamada",
        ],
        "agents/aghuse_backend.toml": [
            "nunca crie uma nova classe `*RN`",
            "crie-a como `*ON`",
        ],
        "agents/aghuse_tests.toml": [
            "Crie, amplie ou corrija testes somente quando a unidade de produção testada for uma classe `*ON` ou uma classe `*RN` existente",
            "Não crie nem modifique testes de controller/action",
            "É permitido ler e executar testes existentes fora de ON/RN apenas para diagnóstico",
            "Antes de criar uma classe de teste, procure uma cobertura adequada no módulo, no restante do repositório e nas branches relacionadas ao fluxo",
            "Só crie uma nova classe após demonstrar que não existe teste adequado",
        ],
        "plugins/aghuse-agent/skills/aghuse-idempotent-database-scripts/SKILL.md": [
            "A mesma regra vale para o rollback",
            "aplicação duas vezes, rollback duas vezes",
            "finalizar a definição da constraint com `ENABLE NOVALIDATE`",
            "Toda foreign key deve possuir um índice associado",
            "Todo `CREATE INDEX` Oracle, inclusive `CREATE UNIQUE INDEX`, deve terminar com `ONLINE`",
            "Não transportar `ENABLE NOVALIDATE` ou `ONLINE` para PostgreSQL",
        ],
        "plugins/aghuse-agent/skills/aghuse-development/SKILL.md": [
            "nunca criar uma nova `*RN`",
            "criá-la como `*ON`",
            "aghuse-idempotent-database-scripts",
            "testes unitários exclusivamente para ONs e RNs existentes",
            "Não delegue ao `aghuse_tests` a criação ou alteração de testes de controller/action",
            "Antes de autorizar uma nova classe `*ONTest` ou `*RNTest`",
            "Prefira ampliar ou portar a classe de teste existente",
            "policy engine central do Jarvis V3",
            "Não fixe modelo ou reasoning por perfil",
            "Somente `MEDIUM` pode escalar uma vez para `HIGH`",
        ],
        "plugins/sfa-agent/skills/sfa-development/SKILL.md": [
            "protocolo Jarvis V3",
            "Não fixe modelo ou reasoning por perfil",
            "somente `MEDIUM` pode escalar uma vez para `HIGH`",
        ],
        "agents/aghuse_database.toml": [
            "aplicação e rollback",
            "deve ser idempotente",
            "Toda nova consulta baseada em Criteria",
            "Não crie novas consultas com `DetachedCriteria`",
            "comentários de dicionário, índices e grants",
            "não duplicar índices simples, compostos ou prefixos já atendidos",
            "princípio do menor privilégio",
            "declare explicitamente a justificativa técnica",
            "finalize a definição da constraint com `ENABLE NOVALIDATE`",
            "Toda foreign key deve possuir um índice associado",
            "Todo `CREATE INDEX` Oracle, inclusive `CREATE UNIQUE INDEX`, deve terminar com a cláusula `ONLINE`",
            "não as copie para scripts PostgreSQL",
        ],
        "agents/sfa_database.toml": [
            "Aplique `DB-DDL-001` nos scripts Oracle",
            "finalize a definição da constraint com `ENABLE NOVALIDATE`",
            "Toda foreign key deve possuir um índice associado",
            "Todo `CREATE INDEX` Oracle, inclusive `CREATE UNIQUE INDEX`, deve terminar com a cláusula `ONLINE`",
            "não as copie para scripts PostgreSQL",
        ],
        "agents/sesab_reviewer.toml": [
            "Ao revisar mudanças no AGHUse",
            "reporte como achado a criação de consultas com `DetachedCriteria`",
        ],
        "plugins/redmine-agent/skills/redmine-workflows/SKILL.md": [
            "confirmação explícita imediatamente antes",
            "Não repetir automaticamente uma escrita",
            "Usar a API REST oficial do Redmine como canal obrigatório",
            "Não usar automação de navegador",
        ],
    }
    for relative, fragments in contracts.items():
        path = ROOT / relative
        if not path.is_file():
            fail(f"Contrato crítico referencia arquivo ausente: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in text:
                fail(f"Contrato crítico ausente em {relative}: {fragment!r}")


def scan_secrets() -> None:
    forbidden = re.compile(r"(?i)(api[_-]?key|password|secret)\s*[=:]\s*['\"][^$<{\[][^'\"]{7,}['\"]")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.name == ".mcp.json":
            continue
        if path.suffix not in {".md", ".json", ".toml", ".yaml", ".yml", ".mjs", ".py", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        scanned = "\n".join(line for line in text.splitlines() if "secret-scan: allow-test-fixture" not in line)
        if forbidden.search(scanned):
            fail(f"Possível segredo literal em {path.relative_to(ROOT)}")


def main() -> int:
    agents = validate_agents()
    plugins = validate_plugins()
    validate_evals(agents)
    validate_versioned_contracts(agents)
    validate_redmine_server()
    validate_aghuse_automation()
    validate_jarvis_runtime()
    validate_reasoning_policy()
    validate_knowledge_transfer_policy()
    validate_critical_contracts()
    scan_secrets()
    if ERRORS:
        print("VALIDAÇÃO FALHOU")
        for error in ERRORS:
            print(f"- {error}")
        return 1
    print(f"OK: {len(plugins)} plugins, {len(agents)} agentes e avaliações válidas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
