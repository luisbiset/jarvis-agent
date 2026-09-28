#!/usr/bin/env python3
"""Interface unificada do Jarvis para os fluxos locais mais usados."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("auditar", "audita credenciais e dados sensíveis"),
        ("resumo-git", "mostra o estado Git sem alterar o repositório"),
        ("simular", "simula uma tarefa sem escrever estado"),
        ("simular-redmine", "consulta uma tarefa Redmine e simula seu fluxo"),
        ("rag", "indexa ou consulta o RAG local"),
        ("executar", "executa um comando do runtime Jarvis"),
        ("painel", "abre o painel local de observabilidade"),
        ("aghuse-analisar", "analisa o impacto de uma tarefa AGHUse"),
    ):
        sub.add_parser(name, help=help_text)
    args, forwarded = parser.parse_known_args()
    scripts = {
        "auditar": ("jarvis_guard.py", "audit"),
        "resumo-git": ("jarvis_guard.py", "git-summary"),
        "simular": ("jarvis_simulate.py",),
        "simular-redmine": ("jarvis_redmine_simulate.py",),
        "rag": ("jarvis_rag.py",),
        "executar": ("jarvis_runtime.py",),
        "painel": ("jarvis_dashboard.py",),
        "aghuse-analisar": ("jarvis_aghuse.py",),
    }
    command = scripts[args.command]
    return subprocess.run([sys.executable, str(ROOT / "scripts" / command[0]), *command[1:], *forwarded], cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
