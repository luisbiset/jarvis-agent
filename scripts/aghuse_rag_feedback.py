#!/usr/bin/env python3
"""Coleta feedback do RAG e promove somente exemplos aprovados ao dataset."""
from __future__ import annotations
import argparse, json, re, secrets
from datetime import datetime, timezone
from pathlib import Path

SECRET = re.compile(r"(?i)(-----BEGIN|bearer\s+|api[_-]?key\s*[=:]|password\s*[=:]|secret\s*[=:]|https?://)")
DEFAULT = Path(".jarvis/rag/feedback.jsonl")

def now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def safe(value: str) -> bool: return isinstance(value, str) and not SECRET.search(value)
def read(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

def suggest_from_pack(path: Path, query: str, rows: list[dict]) -> list[dict]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    if not safe(query): raise ValueError("consulta contém conteúdo não permitido")
    suggestions = []
    for hit in pack.get("hits", []):
        metadata = hit.get("taxonomy", {})
        item = {"id":"fb-" + secrets.token_hex(6), "query":query, "candidate":{"path":hit.get("path", ""), "symbol":hit.get("symbol") or ""}, "relevant":None, "taxonomy":{"layer":metadata.get("layer", "unknown"), "artifact":metadata.get("artifact", "unknown"), "category":metadata.get("category")}, "reason":"Sugestão automática; aguarda aprovação humana.", "match_reasons":hit.get("match_reasons", []), "selection_reason":hit.get("selection_reason", ""), "query_id":pack.get("query_id"), "status":"PENDING", "created_at":now()}
        if item["candidate"]["path"] and safe(item["candidate"]["path"]): suggestions.append(item)
    existing = {(row.get("query_id"), row.get("candidate", {}).get("path")) for row in rows}
    fresh = [item for item in suggestions if (item.get("query_id"), item["candidate"]["path"]) not in existing]
    rows.extend(fresh); return fresh

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--file", type=Path, default=DEFAULT)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add"); add.add_argument("--query", required=True); add.add_argument("--path", required=True); add.add_argument("--symbol", default=""); add.add_argument("--relevant", action="store_true"); add.add_argument("--layer", required=True); add.add_argument("--artifact", required=True); add.add_argument("--reason", default="")
    approve = sub.add_parser("approve"); approve.add_argument("--id", required=True); decision = approve.add_mutually_exclusive_group(required=True); decision.add_argument("--relevant", action="store_true"); decision.add_argument("--irrelevant", action="store_true")
    reject = sub.add_parser("reject"); reject.add_argument("--id", required=True)
    export = sub.add_parser("export"); export.add_argument("--output", type=Path, required=True)
    suggest = sub.add_parser("suggest"); suggest.add_argument("--context-pack", type=Path, required=True); suggest.add_argument("--query", required=True)
    sub.add_parser("list")
    args = parser.parse_args(); rows = read(args.file)
    if args.command == "add":
        values = [args.query, args.path, args.symbol, args.reason, args.layer, args.artifact]
        if any(not safe(value) for value in values): raise SystemExit("feedback contém conteúdo não permitido")
        item = {"id":"fb-" + secrets.token_hex(6), "query":args.query, "candidate":{"path":args.path, "symbol":args.symbol}, "relevant":args.relevant, "taxonomy":{"layer":args.layer, "artifact":args.artifact}, "reason":args.reason, "status":"PENDING", "created_at":now()}
        rows.append(item); write(args.file, rows); print(item["id"])
    elif args.command == "approve":
        found = next((row for row in rows if row["id"] == args.id), None)
        if not found: raise SystemExit("feedback não encontrado")
        found["status"] = "APPROVED"; found["relevant"] = bool(args.relevant); found["approved_at"] = now(); write(args.file, rows); print(args.id)
    elif args.command == "reject":
        found = next((row for row in rows if row["id"] == args.id), None)
        if not found: raise SystemExit("feedback não encontrado")
        found["status"] = "REJECTED"; found["rejected_at"] = now(); write(args.file, rows); print(args.id)
    elif args.command == "list":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.command == "suggest":
        suggestions = suggest_from_pack(args.context_pack, args.query, rows); write(args.file, rows); print(json.dumps({"created":len(suggestions), "pending":sum(row.get("status") == "PENDING" for row in rows), "ids":[row["id"] for row in suggestions]}, ensure_ascii=False))
    else:
        approved = [row for row in rows if row.get("status") == "APPROVED"]
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text("".join(json.dumps({key: row[key] for key in ("query", "candidate", "relevant", "taxonomy", "reason")}, ensure_ascii=False, sort_keys=True) + "\n" for row in approved), encoding="utf-8"); print(json.dumps({"approved":len(approved), "output":str(args.output)}, ensure_ascii=False))
    return 0
if __name__ == "__main__": raise SystemExit(main())
