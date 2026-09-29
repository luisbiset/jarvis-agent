#!/usr/bin/env python3
"""Executa o ciclo seguro de aprendizado do RAG somente com feedback aprovado."""
from __future__ import annotations
import argparse, hashlib, json, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path

from aghuse_rag_dataset import read_examples
from train_rag_reranker import train as train_reranker
from train_taxonomy_classifier import train as train_taxonomy

def now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def load(path: Path) -> list[dict]: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
def promote(source: Path, target: Path, backup: Path) -> None:
    if target.exists(): backup.mkdir(parents=True, exist_ok=True); shutil.copy2(target, backup / target.name)
    target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--feedback", type=Path, default=Path(".jarvis/rag/feedback.jsonl")); parser.add_argument("--root", type=Path, default=Path(".jarvis/rag")); parser.add_argument("--min-examples", type=int, default=2); args = parser.parse_args()
    rows = load(args.feedback); approved = [row for row in rows if row.get("status") == "APPROVED"]; pending = sum(row.get("status") == "PENDING" for row in rows)
    if len(approved) < args.min_examples:
        print(json.dumps({"promoted": False, "reason": "insufficient_approved_examples", "approved": len(approved), "pending": pending, "required": args.min_examples}, ensure_ascii=False)); return 0
    with tempfile.TemporaryDirectory(prefix="jarvis-rag-train-") as temp:
        work = Path(temp); approved_path = work / "approved.jsonl"; write(approved_path, approved); validated = read_examples(approved_path)
        train_rows = [row for row in validated if hashlib.sha256(row["query"].encode()).digest()[0] >= 51]; validation_rows = [row for row in validated if hashlib.sha256(row["query"].encode()).digest()[0] < 51]
        if not train_rows or not validation_rows:
            print(json.dumps({"promoted": False, "reason": "approved_dataset_needs_train_and_validation_split", "approved": len(approved), "pending": pending}, ensure_ascii=False)); return 0
        dataset = work / "dataset"; dataset.mkdir(); write(dataset / "train.jsonl", train_rows); write(dataset / "validation.jsonl", validation_rows)
        reranker, taxonomy = work / "reranker.json", work / "taxonomy.json"
        train_reranker(dataset / "train.jsonl", reranker); train_taxonomy(approved_path, taxonomy)
        backup = args.root / "backups" / datetime.now().strftime("%Y%m%dT%H%M%SZ"); promote(reranker, args.root / "reranker.json", backup); promote(taxonomy, args.root / "taxonomy.json", backup)
        manifest = {"schema_version":"1.0.0", "promoted_at":now(), "approved":len(approved), "train":len(train_rows), "validation":len(validation_rows), "pending":pending, "backup":str(backup) if backup.exists() else None}
        (args.root / "training-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"promoted": True, **manifest}, ensure_ascii=False)); return 0
if __name__ == "__main__": raise SystemExit(main())
