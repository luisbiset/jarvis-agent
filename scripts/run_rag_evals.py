#!/usr/bin/env python3
"""Avalia retrieval offline contra evidências esperadas, sem chamar LLM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.indexer import RagIndex  # noqa: E402
from rag.retriever import search  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--database", type=Path, default=ROOT / ".jarvis/rag/index.db")
    result.add_argument("--cases", type=Path, default=ROOT / "evals/rag-cases.json")
    result.add_argument("--top-k", type=int, default=10)
    return result


def matches(hit: object, expected: dict) -> bool:
    symbols = set(expected.get("symbols_any", []))
    paths = set(expected.get("paths_any", []))
    evidence = (getattr(hit, "symbol", None) in symbols) or (getattr(hit, "path", None) in paths)
    source_types = set(expected.get("source_types", []))
    return bool(evidence and (not source_types or getattr(hit, "source_type", None) in source_types))


def main() -> int:
    args = parser().parse_args()
    if args.top_k < 1:
        print(json.dumps({"error": "top-k deve ser positivo"}), file=sys.stderr); return 2
    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]
    results = []
    with RagIndex(args.database) as index:
        for case in cases:
            hits = search(index, case["query"], args.top_k)
            ranks = [rank for rank, hit in enumerate(hits, 1) if matches(hit, case["expected"])]
            first = min(ranks) if ranks else None
            maximum = case["expected"].get("max_rank", args.top_k)
            results.append({"case_id": case["id"], "recall_at_k": 1.0 if first and first <= maximum else 0.0, "reciprocal_rank": 1 / first if first else 0.0, "budget_compliant": len(hits) <= args.top_k, "fallback_operational": True})
    summary = {"cases": results, "recall_at_k": sum(item["recall_at_k"] for item in results) / len(results) if results else 0, "mrr": sum(item["reciprocal_rank"] for item in results) / len(results) if results else 0}
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(item["recall_at_k"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
