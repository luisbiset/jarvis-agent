#!/usr/bin/env python3
"""Valida a instalação do Jarvis Agent em um CODEX_HOME temporário e isolado."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="jarvis-agent-home-") as temp_dir:
        codex_home = Path(temp_dir)
        env = {**os.environ, "CODEX_HOME": str(codex_home)}
        subprocess.run(
            [str(ROOT / "scripts/install.sh")],
            cwd=ROOT,
            env=env,
            check=True,
        )

        expected_agents = sorted((ROOT / "agents").glob("*.toml"))
        for source in expected_agents:
            installed = codex_home / "agents" / source.name
            if not installed.is_file() or installed.is_symlink():
                raise RuntimeError(f"Agente não foi copiado: {source.name}")
            if installed.read_bytes() != source.read_bytes():
                raise RuntimeError(f"Conteúdo do agente divergiu: {source.name}")

        plugins = subprocess.run(
            ["codex", "plugin", "list"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        output = plugins.stdout + plugins.stderr
        lines = output.splitlines()
        for plugin in ("redmine-agent", "sfa-agent", "aghuse-agent", "sesab-orchestrator"):
            selector = f"{plugin}@codex-agents"
            if not any(selector in line and "installed, enabled" in line for line in lines):
                raise RuntimeError(f"Plugin não foi instalado no perfil temporário: {selector}")

        print(
            f"OK: instalação limpa validada com {len(expected_agents)} agentes e 4 plugins "
            "em perfil temporário."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
