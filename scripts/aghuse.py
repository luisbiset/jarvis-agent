#!/usr/bin/env python3
"""CLI enxuta para o Orchestrator do Codex."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("analisar", "planejar", "implementar", "validar", "manutencao"))
    parser.add_argument("objective")
    parser.add_argument("--project-id", default="aghuse")
    parser.add_argument("--task-id", default=None)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "src"))
    from aghuse_assistant import Orchestrator

    operation = {"analisar": "ANALYZE", "planejar": "PLAN", "implementar": "IMPLEMENT", "validar": "VALIDATE", "manutencao": "MANUTENCAO"}[args.command]
    orchestrator = Orchestrator()
    context = orchestrator.create({"project": args.project_id, "operation": operation, "objective": args.objective, "task_ref": args.task_id})
    print(json.dumps(orchestrator.execute(context, confirm=args.confirm).as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
