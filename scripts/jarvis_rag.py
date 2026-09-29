#!/usr/bin/env python3
"""Indexa e consulta conhecimento local do Jarvis sem chamadas de modelo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.indexer import RagIndex  # noqa: E402
from rag.retriever import retrieve, write_context_pack  # noqa: E402

DEFAULT_DATABASE = ROOT / ".jarvis/rag/index.db"
DEFAULT_RERANKER = ROOT / ".jarvis/rag/reranker.json"
POLICY = ROOT / "contracts/rag-policy.json"


def load_policy(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    root.add_argument("--policy", type=Path, default=POLICY); root.add_argument("--reranker", type=Path, default=None)
    sub = root.add_subparsers(dest="command", required=True)
    index = sub.add_parser("index"); index.add_argument("--repo", type=Path, required=True); index.add_argument("--source-type", default="CODE"); index.add_argument("--taxonomy-model", type=Path)
    search = sub.add_parser("search"); search.add_argument("--query", required=True); search.add_argument("--context-budget", choices=("SMALL", "MEDIUM", "LARGE"), default="MEDIUM"); search.add_argument("--path-filter"); search.add_argument("--repo-filter"); search.add_argument("--branch-filter"); search.add_argument("--source-type-filter"); search.add_argument("--taxonomy", action="append"); search.add_argument("--semantic", action="store_true"); search.add_argument("--output", type=Path)
    sub.add_parser("status")
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "index":
            with RagIndex(args.database) as index:
                model = json.loads(args.taxonomy_model.read_text(encoding="utf-8")) if args.taxonomy_model else None
                result = index.index_repo(args.repo, args.source_type, model)
        elif args.command == "status":
            with RagIndex(args.database) as index:
                result = index.status()
        else:
            taxonomy = dict(item.split("=", 1) for item in (args.taxonomy or []) if "=" in item)
            result = retrieve(args.database, args.query, load_policy(args.policy), args.context_budget, path_filter=args.path_filter, repo_filter=args.repo_filter, branch_filter=args.branch_filter, source_type_filter=args.source_type_filter, taxonomy=taxonomy, reranker_path=args.reranker or (DEFAULT_RERANKER if DEFAULT_RERANKER.is_file() else None), semantic=args.semantic)
            if args.output:
                write_context_pack(args.output, result)
                result = {**result, "output": str(args.output.resolve())}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
