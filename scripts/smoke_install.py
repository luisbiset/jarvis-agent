#!/usr/bin/env python3
"""Valida a instalação do AGHUse Assistant em um CODEX_HOME temporário e isolado."""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aghuse-assistant-home-") as temp_dir:
        codex_home = Path(temp_dir)
        env = {**os.environ, "CODEX_HOME": str(codex_home)}
        command = [str(ROOT / "scripts/install.sh")]
        if sys.platform == "win32":
            bash = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.exe"
            command = [bash, "scripts/install.sh"]
            env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            check=True,
        )

        installed_instructions = codex_home / "AGENTS.md"
        expected_instructions = ROOT / "config/AGENTS.md"
        if not installed_instructions.is_file() or installed_instructions.read_bytes() != expected_instructions.read_bytes():
            raise RuntimeError("Instruções globais de métricas não foram instaladas")
        root_pointer = codex_home / "aghuse-assistant-root"
        if not root_pointer.is_file() or root_pointer.read_text(encoding="utf-8").strip() != str(ROOT):
            raise RuntimeError("Ponteiro do AGHUse Assistant Runtime não foi instalado corretamente")

        expected_agents = sorted((ROOT / "config/agents").glob("*.toml"))
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
        for plugin in ("redmine-agent", "sfa-agent", "aghuse-assistant"):
            selector = f"{plugin}@codex-agents"
            if not any(selector in line and "installed, enabled" in line for line in lines):
                raise RuntimeError(f"Plugin não foi instalado no perfil temporário: {selector}")

        print(
            f"OK: instalação limpa validada com {len(expected_agents)} agentes e 3 plugins "
            "em perfil temporário."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
