#!/usr/bin/env python3
"""Ponte de chat para consulta automÃƒÂ¡tica e segura ao RAG local."""
from __future__ import annotations
import argparse, hashlib, json, re, sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from rag.retriever import retrieve
from prompt_engineer import improve_prompt
SIGNALS = re.compile(r"(?i)(aghuse|c[oÃƒÂ³]digo|classe|m[oÃƒÂ³]dulo|arquivo|bug|erro|corrig|implementar|regra|ejb|jsf|primefaces|dao|facade|entity|xhtml|sql|security|teste|service|controller)")
TASK_REFERENCE = re.compile(r"(?i)(?:tarefa|chamado|os|redmine)\s*#?\s*(\d+)|#\s*(\d+)")
def task_ids(message: str) -> list[int]:
    return sorted({int(group) for match in TASK_REFERENCE.finditer(message) for group in match.groups() if group})
def should_retrieve(message: str) -> bool:
    text = message.strip()
    return len(text) >= 3 and (bool(SIGNALS.search(text)) or bool(TASK_REFERENCE.search(text)))
def retrieve_message(message: str, database: Path, policy_path: Path, context_budget: str = "MEDIUM", semantic: bool = False, *, already_engineered: bool = False) -> dict:
    engineered = {"enhanced": message, "changed": False} if already_engineered else improve_prompt(message)
    query = str(engineered["enhanced"])
    metadata = {"enabled": True, "changed": bool(engineered["changed"])}
    ids = task_ids(query)
    if ids: metadata.update({"task_ids": ids, "redmine_lookup_required": True})
    if not should_retrieve(query): return {"retrieved": False, "reason": "no_code_or_aghuse_signal", "prompt_engineering": metadata}
    if not database.is_file(): return {"retrieved": False, "reason": "rag_index_not_found", "prompt_engineering": metadata}
    result = retrieve(database, query, json.loads(policy_path.read_text(encoding="utf-8")), context_budget, semantic=semantic)
    result["chat_query_hash"] = hashlib.sha256(query.encode()).hexdigest(); result["retrieved"] = True; result["prompt_engineering"] = metadata; return result
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("message"); parser.add_argument("--database", type=Path, default=ROOT / ".jarvis/rag/index.db"); parser.add_argument("--policy", type=Path, default=ROOT / "contracts/rag-policy.json"); parser.add_argument("--output", type=Path); parser.add_argument("--context-budget", choices=("SMALL", "MEDIUM", "LARGE"), default="MEDIUM"); parser.add_argument("--semantic", action="store_true"); args = parser.parse_args()
    started = time.monotonic()
    print("[JARVIS] acionado", file=sys.stderr, flush=True)
    result = retrieve_message(args.message, args.database, args.policy, args.context_budget, args.semantic)
    mode = "RAG" if result.get("retrieved") else "FALLBACK"
    print(f"[JARVIS] modo {mode}: {result.get('reason', 'contexto recuperado')}", file=sys.stderr, flush=True)
    if mode == "FALLBACK" and result.get("reason") != "no_code_or_aghuse_signal":
        print("[JARVIS] bloqueado: anÃƒÂ¡lise RAG nÃƒÂ£o disponÃƒÂ­vel; autorizaÃƒÂ§ÃƒÂ£o explÃƒÂ­cita necessÃƒÂ¡ria", file=sys.stderr, flush=True)
        print(f"[JARVIS] finalizado em {time.monotonic() - started:.2f}s", file=sys.stderr, flush=True)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 2
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[JARVIS] finalizado em {time.monotonic() - started:.2f}s", file=sys.stderr, flush=True)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
