"""Fachada de persistência legada durante a modularização incremental."""
import json
from pathlib import Path
from typing import Any

def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("objeto JSON esperado")
    return value

def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)

def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")

def run_path(value: str | Path) -> Path:
    path = Path(value).resolve()
    if not (path / "state.json").is_file(): raise FileNotFoundError(path)
    return path

__all__ = ["append_jsonl", "load_json", "run_path", "write_json"]
