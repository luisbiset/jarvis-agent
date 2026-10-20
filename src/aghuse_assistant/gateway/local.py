"""Read-only local adapters used by the standalone Assistant CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .gateway import ToolGateway, ToolSpec

_MAX_FILES = 1_000
_MAX_RESULTS = 50
_MAX_FILE_BYTES = 1_000_000
_EXCLUDED_PARTS = {".git", ".aghuse-assistant", "__pycache__", ".venv", "venv"}


def register_local_analysis_tools(gateway: ToolGateway, workspace: Path) -> None:
    """Register bounded, workspace-only search for a local CLI invocation."""
    root = workspace.resolve()
    gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=_code_search(root)))


def _code_search(root: Path):
    def search(*, query: dict[str, Any]) -> list[dict[str, Any]]:
        requirement_id = str(query.get("requirement_id") or "UNKNOWN/NOT_CONFIRMED")
        term = _search_term(str(query.get("term") or ""))
        if not term:
            return []
        findings: list[dict[str, Any]] = []
        files_seen = 0
        for path in sorted(root.rglob("*")):
            if files_seen >= _MAX_FILES or len(findings) >= _MAX_RESULTS:
                break
            if not path.is_file() or _EXCLUDED_PARTS.intersection(path.parts):
                continue
            try:
                resolved = path.resolve()
                relative = resolved.relative_to(root)
                if resolved.stat().st_size > _MAX_FILE_BYTES:
                    continue
                content = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError, ValueError):
                continue
            files_seen += 1
            for line_number, line in enumerate(content.splitlines(), 1):
                if term.casefold() not in line.casefold():
                    continue
                source_path = relative.as_posix()
                findings.append({
                    "requirement_id": requirement_id,
                    "component": relative.stem,
                    "classification": "UNKNOWN",
                    "conclusion": f"Ocorrência local para {term!r}",
                    "type": "CODE",
                    "source_id": f"{source_path}:{line_number}",
                    "source": {"path": source_path, "line": line_number},
                })
                if len(findings) >= _MAX_RESULTS:
                    break
        return findings

    return search


def _search_term(value: str) -> str:
    """Remove the investigation-area prefix from ``<area>: <requirement>``."""
    _, separator, term = value.partition(":")
    return (term if separator else value).strip()
