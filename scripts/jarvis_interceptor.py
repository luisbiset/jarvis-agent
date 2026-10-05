"""Interceptor único para mensagens que exigem contexto técnico do Jarvis."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TECHNICAL = re.compile(r"(?i)(aghuse|codigo|classe|m[oó]dulo|arquivo|bug|erro|corrig|implementar|regra|ejb|jsf|primefaces|dao|facade|entity|xhtml|sql|security|teste|service|controller|redmine|chamado|tarefa)")
TASK_REFERENCE = re.compile(r"(?i)(?:tarefa|chamado|os|redmine)\s*#?\s*(\d+)|#\s*(\d+)")

def task_ids(message: str) -> list[int]:
    return sorted({int(value) for match in TASK_REFERENCE.finditer(message) for value in match.groups() if value})

def is_technical(message: str) -> bool:
    return len(message.strip()) >= 3 and bool(TECHNICAL.search(message))

def intercept(message: str, *, database: Path, policy: Path, context_budget: str = "SMALL", semantic: bool = False, bypass: str | None = None) -> dict[str, Any]:
    ids = task_ids(message)
    if not is_technical(message):
        return {"required": False, "technical": False, "task_ids": ids, "retrieved": False, "reason": "non_technical_message"}
    if bypass and bypass.strip():
        return {"required": True, "technical": True, "bypassed": True, "blocked": False, "bypass_reason": bypass.strip(), "task_ids": ids, "retrieved": False, "reason": "explicit_rag_bypass", "message_hash": hashlib.sha256(message.encode()).hexdigest()}
    try:
        from jarvis_chat_rag import retrieve_message
    except ModuleNotFoundError:
        from scripts.jarvis_chat_rag import retrieve_message
    result = retrieve_message(message, database, policy, context_budget, semantic)
    result.update({"required": True, "technical": True, "task_ids": ids})
    result["blocked"] = not result.get("retrieved") and result.get("reason") != "no_code_or_aghuse_signal"
    return result

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message"); parser.add_argument("--database", type=Path, default=ROOT / ".jarvis/rag/index.db"); parser.add_argument("--policy", type=Path, default=ROOT / "contracts/rag-policy.json"); parser.add_argument("--context-budget", choices=("SMALL", "MEDIUM", "LARGE"), default="MEDIUM"); parser.add_argument("--semantic", action="store_true"); parser.add_argument("--allow-rag-bypass", metavar="REASON")
    args = parser.parse_args(); result = intercept(args.message, database=args.database, policy=args.policy, context_budget=args.context_budget, semantic=args.semantic, bypass=args.allow_rag_bypass)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not result.get("blocked") else 2

if __name__ == "__main__": raise SystemExit(main())
