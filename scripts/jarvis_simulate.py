#!/usr/bin/env python3
"""Simula o fluxo Jarvis sem criar runs, escrever arquivos ou chamar serviços."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.jarvis_runtime import reasoning_decision, task_signals_from_args  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--task-type", default="GENERAL")
    parser.add_argument("--estimated-files", type=int, default=0)
    parser.add_argument("--estimated-modules", type=int, default=0)
    parser.add_argument("--security-sensitive", action="store_true")
    parser.add_argument("--database-migration", action="store_true")
    parser.add_argument("--tests-required", action="store_true")
    args = parser.parse_args()
    decision = reasoning_decision(task_signals_from_args(args))
    print(json.dumps({
        "simulation": True,
        "task_id": args.task_id,
        "operational_mode": "READ_ONLY_AUDIT",
        "planned_stages": ["DISCOVERY", "PLAN_READY", "VALIDATING", "REVIEW_READY"],
        "external_actions": "blocked",
        "reasoning": decision,
        "writes_performed": 0,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
