#!/usr/bin/env python3
"""Gateway local: toda mensagem recebida passa pelo engenheiro antes do chat."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?", help="mensagem a encaminhar")
    parser.add_argument("--show-enhanced", action="store_true")
    parser.add_argument("--allow-rag-bypass", metavar="REASON")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--context-budget", choices=("SMALL", "MEDIUM", "LARGE"), default="SMALL")
    parser.add_argument("--semantic", action="store_true")
    args = parser.parse_args()
    message = args.message or sys.stdin.read().strip()
    if not message:
        parser.error("informe uma mensagem ou envie texto pela entrada padrão")
    command = [sys.executable, str(ROOT / "scripts" / "jarvis_chat.py"), message]
    if args.show_enhanced:
        command.append("--show-enhanced")
    if args.allow_rag_bypass:
        command.extend(["--allow-rag-bypass", args.allow_rag_bypass])
    for flag, value in (("--database", args.database), ("--policy", args.policy), ("--context-budget", args.context_budget)):
        if value:
            command.extend([flag, str(value)])
    if args.semantic:
        command.append("--semantic")
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
