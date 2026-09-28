#!/usr/bin/env python3
"""Valida e divide dataset supervisionado local do reranker AGHUse."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

SECRET = re.compile(r"(?i)(-----BEGIN|bearer\s+|api[_-]?key\s*[=:]|password\s*[=:]|secret\s*[=:]|https?://)")

def read_examples(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip(): continue
        item = json.loads(line); candidate = item.get("candidate", {})
        values = [item.get("query"), candidate.get("path"), candidate.get("symbol", ""), item.get("reason", "")]
        if any(not isinstance(value, str) or SECRET.search(value) for value in values):
            raise ValueError(f"exemplo {number} contém conteúdo não permitido")
        if not isinstance(item.get("relevant"), bool) or not candidate.get("path"):
            raise ValueError(f"exemplo {number} possui esquema inválido")
        rows.append(item)
    if not rows: raise ValueError("dataset vazio")
    return rows

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("build", nargs="?"); parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    rows = read_examples(args.input); train, validation = [], []
    for row in rows:
        bucket = hashlib.sha256(row["query"].encode()).digest()[0]
        (validation if bucket < 51 else train).append(row)
    if not train or not validation: raise ValueError("dataset precisa conter consultas suficientes para treino e validação")
    args.output.mkdir(parents=True, exist_ok=True)
    for name, values in (("train.jsonl", train), ("validation.jsonl", validation)):
        (args.output / name).write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in values), encoding="utf-8")
    manifest = {"schema_version":"1.0.0", "examples":len(rows), "train":len(train), "validation":len(validation), "input_sha256":hashlib.sha256(args.input.read_bytes()).hexdigest()}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
