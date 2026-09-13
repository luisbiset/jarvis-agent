"""Filtros conservadores aplicados antes de persistir ou embeddingar conteúdo."""

from __future__ import annotations

import re
from pathlib import Path

IGNORED_PARTS = {".git", ".jarvis", "node_modules", "target", "build", "dist", ".idea", ".vscode", "__pycache__"}
IGNORED_NAMES = {".env", ".mcp.json", "id_rsa", "id_ed25519"}
TEXT_SUFFIXES = {".java", ".sql", ".md", ".json", ".toml", ".py", ".mjs", ".js", ".ts", ".xhtml", ".xml", ".yml", ".yaml", ".sh"}
SENSITIVE = re.compile(
    r"(?i)(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|bearer\s+[a-z0-9._-]{12,}|"
    r"(?:api[_-]?key|password|passwd|secret|credential|authorization)\s*[=:]\s*[^\s$<{]{4,})"
)


def eligible(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return (
        path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and path.name not in IGNORED_NAMES
        and not any(part in IGNORED_PARTS for part in relative.parts)
        and not any(part.startswith(".") and part not in {".agents", ".codex-plugin"} for part in relative.parts)
    )


def safe_text(text: str) -> bool:
    return not SENSITIVE.search(text)
