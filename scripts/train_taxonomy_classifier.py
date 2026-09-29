#!/usr/bin/env python3
"""Treina classificador local de taxonomia por termos rotulados."""
from __future__ import annotations
import argparse, collections, json, re
from pathlib import Path

TOKEN = re.compile(r"[\w.-]{2,}", re.UNICODE)
def features(row: dict) -> set[str]:
    candidate = row["candidate"]
    return {x.casefold() for x in TOKEN.findall(candidate["path"] + " " + candidate.get("symbol", ""))}

def train(input_path: Path, output: Path) -> dict:
    rows = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = {"layer": collections.defaultdict(collections.Counter), "artifact": collections.defaultdict(collections.Counter), "category": collections.defaultdict(collections.Counter)}
    for row in rows:
        taxonomy = row.get("taxonomy", {})
        for field in labels:
            values = taxonomy.get("categories", [taxonomy[field]]) if field == "category" and ("categories" in taxonomy or field in taxonomy) else ([taxonomy[field]] if field in taxonomy else [])
            for value in values: labels[field][value].update(features(row))
    model = {"schema_version":"1.0.0", "method":"taxonomy_term_counts", "labels":{field:{label:dict(counts) for label, counts in values.items()} for field, values in labels.items()}}
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); return model

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    model = train(args.input, args.output)
    print(json.dumps({"output":str(args.output), "labels":{key:len(value) for key,value in model["labels"].items()}}, ensure_ascii=False)); return 0
if __name__ == "__main__": raise SystemExit(main())
