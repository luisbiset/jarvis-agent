#!/usr/bin/env python3
"""Operações explícitas e auditáveis sobre modelos locais do RAG."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("rollback", "status"))
    parser.add_argument("--root", type=Path, default=Path(".jarvis/rag"))
    args = parser.parse_args()
    root = args.root.resolve()
    backups = sorted((root / "backups").glob("*") if (root / "backups").is_dir() else [], reverse=True)
    if args.command == "status":
        manifest = root / "training-manifest.json"
        print(json.dumps({"root": str(root), "active": [name for name in ("reranker.json", "taxonomy.json") if (root / name).is_file()], "backups": [str(path) for path in backups], "manifest": json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else None}, ensure_ascii=False))
        return 0
    if not backups:
        raise SystemExit("nenhum backup de modelo disponível para rollback")
    backup = backups[0]
    restored = []
    for name in ("reranker.json", "taxonomy.json"):
        source = backup / name
        if source.is_file():
            shutil.copy2(source, root / name)
            restored.append(name)
    if not restored:
        raise SystemExit("backup não contém modelos restauráveis")
    event = {"event": "MODEL_ROLLBACK", "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "backup": str(backup), "restored": restored}
    (root / "rollback-manifest.json").write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(event, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
