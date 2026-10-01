#!/usr/bin/env python3
"""Ciclo de entrada de mensagem do Jarvis: RAG antes do planejamento."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from jarvis_chat_rag import ROOT, retrieve_message
from prompt_engineer import improve_prompt
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("message"); parser.add_argument("--database", type=Path, default=ROOT / ".jarvis/rag/index.db"); parser.add_argument("--policy", type=Path, default=ROOT / "contracts/rag-policy.json"); parser.add_argument("--context-budget", choices=("SMALL", "MEDIUM", "LARGE"), default="MEDIUM"); parser.add_argument("--semantic", action="store_true"); parser.add_argument("--show-enhanced", action="store_true", help="exibe o prompt estruturado usado internamente"); parser.add_argument("--output", type=Path); args = parser.parse_args()
    engineered = improve_prompt(args.message)
    result = {"message_received": True, "stage": "RAG_BEFORE_PLANNING", "prompt_engineering": {"enabled": True, "changed": engineered["changed"]}, "rag": retrieve_message(str(engineered["enhanced"]), args.database, args.policy, args.context_budget, args.semantic, already_engineered=True)}
    if args.show_enhanced: result["enhanced_message"] = engineered["enhanced"]
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
