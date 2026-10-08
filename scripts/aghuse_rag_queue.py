#!/usr/bin/env python3
"""Fila local, segura e idempotente para treinamento assistido do RAG."""
from __future__ import annotations
import argparse, json, secrets
from datetime import datetime, timezone
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / ".aghuse-assistant/rag/training-queue.jsonl"
def now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")
def read(path: Path) -> list[dict]: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []
def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--file", type=Path, default=DEFAULT); sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("enqueue"); sub.add_parser("list"); sub.add_parser("run-once")
    args = parser.parse_args(); rows = read(args.file)
    if args.command == "enqueue":
        if any(row.get("status") in {"PENDING", "RUNNING"} for row in rows): print(json.dumps({"enqueued": False, "reason": "training_already_queued"}, ensure_ascii=False)); return 0
        item = {"id": "train-" + secrets.token_hex(6), "status": "PENDING", "created_at": now()}; rows.append(item); write(args.file, rows); print(json.dumps(item, ensure_ascii=False)); return 0
    if args.command == "list": print(json.dumps(rows, ensure_ascii=False, indent=2)); return 0
    item = next((row for row in rows if row.get("status") == "PENDING"), None)
    if not item: print(json.dumps({"processed": False, "reason": "queue_empty"}, ensure_ascii=False)); return 0
    item["status"] = "RUNNING"; item["started_at"] = now(); write(args.file, rows)
    result = run([__import__("sys").executable, str(ROOT / "scripts/aghuse_rag_auto_train.py")], cwd=ROOT, text=True, capture_output=True)
    item["status"] = "DONE" if result.returncode == 0 else "FAILED"; item["finished_at"] = now(); item["output"] = result.stdout[-4000:]; item["error"] = result.stderr[-2000:]; write(args.file, rows)
    print(json.dumps({"processed": True, "id": item["id"], "status": item["status"], "output": result.stdout}, ensure_ascii=False)); return result.returncode
if __name__ == "__main__": raise SystemExit(main())
