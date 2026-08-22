#!/usr/bin/env python3
"""Validação determinística e sem dependências do projeto Jarvis Agent."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


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
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        fail("Schema do resultado dos evals deve ser um objeto fechado")
    ids: set[str] = set()
    allowed_invariants = {"create-on-not-rn", "idempotent-apply-and-rollback"}
    required_fields = {
        "id",
        "prompt",
        "expected_skills",
        "expected_agents",
        "forbidden_agents",
        "requires_confirmation",
        "read_only",
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
        for field in ("expected_skills", "expected_agents", "forbidden_agents", "invariants"):
            if field in case and not isinstance(case[field], list):
                fail(f"Avaliação {case_id} possui {field} inválido")
        for field in ("requires_confirmation", "read_only"):
            if not isinstance(case.get(field), bool):
                fail(f"Avaliação {case_id} possui {field} inválido")
        for skill in case.get("expected_skills", []):
            if skill not in known_skills:
                fail(f"Avaliação {case_id} referencia skill desconhecida: {skill}")
        for agent in case.get("expected_agents", []) + case.get("forbidden_agents", []):
            if agent not in agent_names:
                fail(f"Avaliação {case_id} referencia agente desconhecido: {agent}")
        overlap = set(case.get("expected_agents", [])) & set(case.get("forbidden_agents", []))
        if overlap:
            fail(f"Avaliação {case_id} exige e proíbe os mesmos agentes: {sorted(overlap)}")
        unknown_invariants = set(case.get("invariants", [])) - allowed_invariants
        if unknown_invariants:
            fail(f"Avaliação {case_id} possui invariantes desconhecidas: {sorted(unknown_invariants)}")


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


def validate_critical_contracts() -> None:
    contracts = {
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
        ],
        "plugins/aghuse-agent/skills/aghuse-development/SKILL.md": [
            "nunca criar uma nova `*RN`",
            "criá-la como `*ON`",
            "aghuse-idempotent-database-scripts",
            "testes unitários exclusivamente para ONs e RNs existentes",
            "Não delegue ao `aghuse_tests` a criação ou alteração de testes de controller/action",
            "Antes de autorizar uma nova classe `*ONTest` ou `*RNTest`",
            "Prefira ampliar ou portar a classe de teste existente",
        ],
        "agents/aghuse_database.toml": [
            "aplicação e rollback",
            "deve ser idempotente",
            "Toda nova consulta baseada em Criteria",
            "Não crie novas consultas com `DetachedCriteria`",
        ],
        "agents/sesab_reviewer.toml": [
            "Ao revisar mudanças no AGHUse",
            "reporte como achado a criação de consultas com `DetachedCriteria`",
        ],
        "plugins/redmine-agent/skills/redmine-workflows/SKILL.md": [
            "confirmação explícita imediatamente antes",
            "Não repetir automaticamente uma escrita",
        ],
        "plugins/sesab-orchestrator/skills/sesab-orchestration/SKILL.md": [
            "redmine-workflows",
            "sfa-development",
            "aghuse-development",
            "sesab_reviewer",
            "qa_homologacao",
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
    validate_redmine_server()
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
