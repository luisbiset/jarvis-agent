#!/usr/bin/env python3
"""Gera documentação determinística da topologia a partir dos contratos reais."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/TOPOLOGY.md"


def escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    header = text.split("---\n", 2)[1]
    data = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def render() -> str:
    version = json.loads((ROOT / "contracts/version.json").read_text(encoding="utf-8"))
    lines = [
        "# Topologia gerada do Jarvis Agent",
        "",
        "> Arquivo gerado por `python3 scripts/generate_topology.py`. Não editar manualmente.",
        "",
        f"Versão comportamental: `{version['jarvis_version']}`.",
        "",
        "## Plugins",
        "",
        "| Plugin | Versão | Skills |",
        "|---|---|---:|",
    ]
    for plugin_dir in sorted((ROOT / "plugins").iterdir()):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / ".codex-plugin/plugin.json"
        if not manifest_path.is_file():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        skill_count = len(list((plugin_dir / "skills").glob("*/SKILL.md")))
        lines.append(f"| {escape(manifest['name'])} | `{escape(manifest['version'])}` | {skill_count} |")

    lines.extend(
        [
            "",
            "## Agentes",
            "",
            "| Agente | Reasoning padrão | Sandbox | Responsabilidade |",
            "|---|---|---|---|",
        ]
    )
    for path in sorted((ROOT / "agents").glob("*.toml")):
        with path.open("rb") as stream:
            agent = tomllib.load(stream)
        lines.append(
            f"| {escape(agent['name'])} | {escape(agent.get('model_reasoning_effort', 'adaptive'))} | "
            f"{escape(agent.get('sandbox_mode', 'workspace-write'))} | {escape(agent['description'])} |"
        )

    lines.extend(["", "## Skills", "", "| Plugin | Skill | Roteamento |", "|---|---|---|"])
    for path in sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md")):
        data = frontmatter(path)
        plugin = path.parents[2].name
        lines.append(f"| {escape(plugin)} | {escape(data.get('name', path.parent.name))} | {escape(data.get('description', ''))} |")

    policies = json.loads((ROOT / "contracts/policy-registry.json").read_text(encoding="utf-8"))["policies"]
    lines.extend(["", "## Políticas", "", "| ID | Categoria | Resumo |", "|---|---|---|"])
    for policy in policies:
        lines.append(f"| `{escape(policy['id'])}` | {escape(policy['category'])} | {escape(policy['summary'])} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Falha se o arquivo gerado estiver desatualizado.")
    args = parser.parse_args()
    content = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != content:
            print(f"desatualizado: {OUTPUT.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print(f"OK: {OUTPUT.relative_to(ROOT)} está sincronizado.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Gerado: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
