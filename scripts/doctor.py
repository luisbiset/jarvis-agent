#!/usr/bin/env python3
"""Diagn\u00f3stico read-only da instala\u00e7\u00e3o local do Jarvis Agent."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
FAILURES: list[str] = []
ATTENTION = "ATEN\u00c7\u00c3O"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def status(ok: bool, message: str) -> None:
    if not ok:
        FAILURES.append(message)
    print(f"{'OK' if ok else ATTENTION}: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Retorna c\u00f3digo diferente de zero quando qualquer diagn\u00f3stico falha.")
    return parser.parse_args()


def agent_is_installed(path: Path, expected: Path) -> bool:
    return path.is_file() and not path.is_symlink() and path.read_bytes() == expected.read_bytes()


def redmine_diagnostic(config: dict, plugin_enabled: bool, central_server: str) -> tuple[bool, str]:
    """Aceita configura\u00e7\u00e3o MCP expl\u00edcita ou o plugin global habilitado."""
    redmine = config.get("mcp_servers", {}).get("redmine", {})
    if central_server in redmine.get("args", []):
        return True, "MCP Redmine configurado via mcp_servers"
    if plugin_enabled:
        return True, "plugin Redmine instalado e habilitado"
    return False, "MCP Redmine n\u00e3o encontrado ou apontando para outro projeto"


def main() -> int:
    cli_args = parse_args()
    global_instructions = CODEX_HOME / "AGENTS.md"
    expected_global_instructions = ROOT / "config/AGENTS.md"
    status(agent_is_installed(global_instructions, expected_global_instructions), "instru\u00e7\u00f5es globais de m\u00e9tricas instaladas")
    root_pointer = CODEX_HOME / "jarvis-agent-root"
    status(root_pointer.is_file() and root_pointer.read_text(encoding="utf-8").strip() == str(ROOT), "ponteiro global do Jarvis Runtime aponta para o projeto central")
    expected_agents = {path.name: path.resolve() for path in (ROOT / "agents").glob("*.toml")}
    installed_agents = CODEX_HOME / "agents"
    for name, target in sorted(expected_agents.items()):
        status(agent_is_installed(installed_agents / name, target), f"agente global {name} copiado a partir de {target}")
    status(not (installed_agents / "sesab_orchestrator.toml").exists(), "agente removido sesab_orchestrator n\u00e3o est\u00e1 ativo")

    config_path = CODEX_HOME / "config.toml"
    config = {}
    if config_path.is_file():
        with config_path.open("rb") as stream:
            config = tomllib.load(stream)
    codex_command = "codex.cmd" if os.name == "nt" else "codex"
    result = subprocess.run([codex_command, "plugin", "list"], capture_output=True, text=True)
    lines = (result.stdout + result.stderr).splitlines()
    redmine_selector = "redmine-agent@codex-agents"
    redmine_enabled = any(redmine_selector in line and "installed, enabled" in line for line in lines)
    central_server = str(ROOT / "plugins/redmine-agent/scripts/server.mjs")
    redmine_ok, redmine_message = redmine_diagnostic(config, redmine_enabled, central_server)
    status(redmine_ok, redmine_message)
    status(bool(os.environ.get("REDMINE_API_KEY")), "REDMINE_API_KEY dispon\u00edvel sem exibir o valor")
    for plugin in ("redmine-agent", "sfa-agent", "aghuse-agent"):
        selector = f"{plugin}@codex-agents"
        enabled = any(selector in line and "installed, enabled" in line for line in lines)
        status(enabled, f"plugin {selector} instalado")
    duplicates = [name for name in ("redmine-agent@personal", "sfa-agent@personal") if any(name in line and "installed, enabled" in line for line in lines)]
    status(not duplicates, f"sem plugins legados ativos{': ' + ', '.join(duplicates) if duplicates else ''}")
    removed_selector = "sesab-orchestrator@codex-agents"
    status(not any(removed_selector in line and "installed, enabled" in line for line in lines), f"plugin removido {removed_selector} n\u00e3o est\u00e1 ativo")
    legacy_skills = [Path.home() / ".agents/skills/redmine-workflows", Path.home() / ".agents/skills/sfa-development"]
    active_legacy = [str(path) for path in legacy_skills if path.exists() or path.is_symlink()]
    status(not active_legacy, f"sem symlinks legados de skills{': ' + ', '.join(active_legacy) if active_legacy else ''}")
    if FAILURES:
        print(f"Resumo: {len(FAILURES)} verifica\u00e7\u00e3o(\u00f5es) requerem aten\u00e7\u00e3o.")
        return 1 if cli_args.strict else 0
    print("Resumo: instala\u00e7\u00e3o saud\u00e1vel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
