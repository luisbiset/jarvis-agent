"""Read-only local adapters used by the standalone Assistant CLI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..analysis.interpreter import search_terms
from .gateway import ToolGateway, ToolSpec

_MAX_FILES = 1_000
_MAX_RESULTS = 50
_MAX_FILE_BYTES = 1_000_000
_EXCLUDED_PARTS = {".git", ".aghuse-assistant", "__pycache__", ".venv", "venv"}
_AREA_PATH_HINTS = {
    "entidade": ("entidade", "entity", "model"),
    "dao": ("dao", "repository"),
    "on/rn": ("on", "rn", "regra", "business"),
    "ejb": ("ejb", "service"),
    "xhtml": ("xhtml", "view", "web", "page"),
    "segurança": ("security", "segur", "auth", "login", "permission"),
    "banco": ("sql", "migration", "schema", "database", "db"),
    "testes": ("test", "spec"),
}


def register_local_analysis_tools(gateway: ToolGateway, workspace: Path) -> None:
    """Register bounded, workspace-only search for a local CLI invocation."""
    root = workspace.resolve()
    gateway.register(ToolSpec("code.search", "analysis", "workspace", handler=_code_search(root)))


def _code_search(root: Path):
    def search(*, query: dict[str, Any]) -> list[dict[str, Any]]:
        requirement_id = str(query.get("requirement_id") or "UNKNOWN/NOT_CONFIRMED")
        area, requirement = _query_parts(str(query.get("term") or ""))
        terms = search_terms(requirement)
        if not terms:
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
                if not _matches_area(relative, area):
                    continue
                if resolved.stat().st_size > _MAX_FILE_BYTES:
                    continue
                content = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError, ValueError):
                continue
            files_seen += 1
            for line_number, line in enumerate(content.splitlines(), 1):
                normalized_line = " ".join(search_terms(line))
                matched_terms = tuple(term for term in terms if term in normalized_line)
                if not matched_terms:
                    continue
                source_path = relative.as_posix()
                findings.append({
                    "requirement_id": requirement_id,
                    "component": relative.stem,
                    "classification": "CONDITIONAL",
                    "conclusion": f"Termos locais compatíveis na área {area}: {', '.join(matched_terms)}",
                    "type": "CODE",
                    "source_id": f"{source_path}:{line_number}",
                    "source": {"path": source_path, "line": line_number},
                    "matched_terms": matched_terms,
                    "excerpt": line.strip()[:240],
                })
                if len(findings) >= _MAX_RESULTS:
                    break
        return findings

    return search


def _query_parts(value: str) -> tuple[str, str]:
    """Split the investigation query without losing the explicit area context."""
    area, separator, term = value.partition(":")
    return (area if separator else "código").strip().casefold(), (term if separator else value).strip()


def _matches_area(path: Path, area: str) -> bool:
    hints = _AREA_PATH_HINTS.get(area)
    if not hints:
        return True
    value = path.as_posix().casefold()
    return any(hint in value for hint in hints)
