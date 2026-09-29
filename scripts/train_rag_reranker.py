#!/usr/bin/env python3
"""Treina um reranker local leve por pesos de termos, sem GPU ou dependências."""
from __future__ import annotations
import argparse, collections, json, math, re
from pathlib import Path

TOKEN = re.compile(r"[\w.-]{2,}", re.UNICODE)
def tokens(value: str) -> set[str]: return {x.casefold() for x in TOKEN.findall(value)}
def features(row: dict) -> set[str]:
    candidate = row["candidate"]; return tokens(row["query"]) | {"path:" + x for x in tokens(candidate["path"])} | {"symbol:" + x for x in tokens(candidate.get("symbol", ""))}

def train(train_path: Path, output: Path) -> dict:
    rows = [json.loads(line) for line in train_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    positive = collections.Counter(); negative = collections.Counter()
    for row in rows: (positive if row["relevant"] else negative).update(features(row))
    total_positive, total_negative = max(1, sum(positive.values())), max(1, sum(negative.values()))
    vocabulary = sorted(set(positive) | set(negative)); weights = {term: round(math.log((positive[term] + 1) / total_positive / ((negative[term] + 1) / total_negative)), 6) for term in vocabulary}
    model = {"schema_version":"1.0.0", "method":"term_log_odds", "examples":len(rows), "weights":weights}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return model

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--train", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    model = train(args.train, args.output)
    print(json.dumps({"output":str(args.output), "examples":len(rows), "features":len(weights)}, ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
