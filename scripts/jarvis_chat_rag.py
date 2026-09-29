#!/usr/bin/env python3
"""Ponte de chat para consulta automática e segura ao RAG local."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from rag.retriever import retrieve
SIGNALS = re.compile(r"(?i)(aghuse|c[oó]digo|classe|m[oó]dulo|arquivo|bug|erro|corrig|implementar|regra|ejb|jsf|primefaces|dao|facade|entity|xhtml|sql|security|teste|service|controller)")
def should_retrieve(message: str) -> bool: return bool(SIGNALS.search(message)) and len(message.strip()) >= 12
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("message"); parser.add_argument("--database", type=Path, default=ROOT / ".jarvis/rag/index.db"); parser.add_argument("--policy", type=Path, default=ROOT / "contracts/rag-policy.json"); parser.add_argument("--output", type=Path); parser.add_argument("--context-budget", choices=("SMALL", "MEDIUM", "LARGE"), default="MEDIUM"); args = parser.parse_args()
    if not should_retrieve(args.message): result = {"retrieved": False, "reason": "no_code_or_aghuse_signal"}
    elif not args.database.is_file(): result = {"retrieved": False, "reason": "rag_index_not_found"}
    else:
        result = retrieve(args.database, args.message, json.loads(args.policy.read_text(encoding="utf-8")), args.context_budget); result["chat_query_hash"] = hashlib.sha256(args.message.encode()).hexdigest(); result["retrieved"] = True
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
