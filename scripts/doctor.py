#!/usr/bin/env python3
"""Diagnóstico read-only da instalação local do Jarvis Agent."""

from __future__ import annotations

import argparse
import os
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


FAILURES: list[str] = []


def status(ok: bool, message: str) -> None:
    if not ok:
        FAILURES.append(message)
    print(f"{'OK' if ok else 'ATENÇÃO'}: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Retorna código diferente de zero quando qualquer diagnóstico falha.",
    )
    return parser.parse_args()


def agent_is_installed(path: Path, expected: Path) -> bool:
    return path.is_file() and not path.is_symlink() and path.read_bytes() == expected.read_bytes()


def main() -> int:
    cli_args = parse_args()
    global_instructions = CODEX_HOME / "AGENTS.md"
    expected_global_instructions = ROOT / "config/AGENTS.md"
    status(
        agent_is_installed(global_instructions, expected_global_instructions),
        "instruções globais de métricas instaladas",
    )
    root_pointer = CODEX_HOME / "jarvis-agent-root"
    status(
        root_pointer.is_file() and root_pointer.read_text(encoding="utf-8").strip() == str(ROOT),
        "ponteiro global do Jarvis Runtime aponta para o projeto central",
    )
    expected_agents = {path.name: path.resolve() for path in (ROOT / "agents").glob("*.toml")}
    installed_agents = CODEX_HOME / "agents"
    for name, target in sorted(expected_agents.items()):
        installed = installed_agents / name
        status(
            agent_is_installed(installed, target),
            f"agente global {name} copiado a partir de {target}",
        )
    removed_agent = installed_agents / "sesab_orchestrator.toml"
    status(not removed_agent.exists(), "agente removido sesab_orchestrator não está ativo")

    config_path = CODEX_HOME / "config.toml"
    config = {}
    if config_path.is_file():
        with config_path.open("rb") as stream:
            config = tomllib.load(stream)
    redmine = config.get("mcp_servers", {}).get("redmine", {})
    redmine_args = redmine.get("args", [])
    central_server = str(ROOT / "plugins/redmine-agent/scripts/server.mjs")
    status(central_server in redmine_args, "MCP Redmine aponta para o projeto central")
    status(bool(os.environ.get("REDMINE_API_KEY")), "REDMINE_API_KEY disponível sem exibir o valor")

    result = subprocess.run(["codex", "plugin", "list"], capture_output=True, text=True)
    output = result.stdout + result.stderr
    lines = output.splitlines()
    for plugin in ("redmine-agent", "sfa-agent", "aghuse-agent"):
        selector = f"{plugin}@codex-agents"
        enabled = any(selector in line and "installed, enabled" in line for line in lines)
        status(enabled, f"plugin {selector} instalado")
    duplicates = [
        name
        for name in ("redmine-agent@personal", "sfa-agent@personal")
        if any(name in line and "installed, enabled" in line for line in lines)
    ]
    status(not duplicates, f"sem plugins legados ativos{': ' + ', '.join(duplicates) if duplicates else ''}")
    removed_selector = "sesab-orchestrator@codex-agents"
    status(
        not any(removed_selector in line and "installed, enabled" in line for line in lines),
        f"plugin removido {removed_selector} não está ativo",
    )

    legacy_skills = [Path.home() / ".agents/skills/redmine-workflows", Path.home() / ".agents/skills/sfa-development"]
    active_legacy = [str(path) for path in legacy_skills if path.exists() or path.is_symlink()]
    status(not active_legacy, f"sem symlinks legados de skills{': ' + ', '.join(active_legacy) if active_legacy else ''}")
    if FAILURES:
        print(f"Resumo: {len(FAILURES)} verificação(ões) requerem atenção.")
        return 1 if cli_args.strict else 0
    print("Resumo: instalação saudável.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
