"""Chunking estrutural determinístico, com fallback por seções e linhas."""

from __future__ import annotations

import re
from pathlib import Path

from .models import Chunk

JAVA_SYMBOL = re.compile(r"^\s*(?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)*(?:class|interface|enum|record)\s+(\w+)|^\s*(?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)+(?:[\w<>\[\],.?]+\s+)+(\w+)\s*\(")
PY_SYMBOL = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)")
JS_SYMBOL = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function|class)\s+(\w+)|^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SQL_START = re.compile(r"^\s*(?:create(?:\s+or\s+replace)?\s+(?:procedure|function|trigger|view|table)|alter\s+table|insert\s+into|update\s+|delete\s+from|merge\s+into)", re.I)
TOML_SECTION = re.compile(r"^\s*\[\[?([^\]]+)\]\]?\]\s*$")
JSON_KEY = re.compile(r'^\s{0,4}"([^"\\]+)"\s*:')


def _emit(path: str, language: str, chunk_type: str, lines: list[str], start: int, end: int, symbol: str | None = None) -> Chunk | None:
    text = "".join(lines[start - 1:end]).strip()
    if not text:
        return None
    return Chunk(path, language, chunk_type, start, end, text, symbol)


def _symbol_chunks(path: str, lines: list[str], language: str, pattern: re.Pattern[str]) -> list[Chunk]:
    starts: list[tuple[int, str]] = []
    for number, line in enumerate(lines, 1):
        match = pattern.search(line)
        if match:
            starts.append((number, next(group for group in match.groups() if group)))
    if not starts:
        return []
    chunks = []
    for index, (start, symbol) in enumerate(starts):
        end = (starts[index + 1][0] - 1) if index + 1 < len(starts) else len(lines)
        item = _emit(path, language, "SYMBOL", lines, start, end, symbol)
        if item:
            chunks.extend(_split_large(item))
    return chunks


def _split_large(chunk: Chunk, max_lines: int = 180, overlap: int = 12) -> list[Chunk]:
    lines = chunk.text.splitlines()
    if len(lines) <= max_lines:
        return [chunk]
    result = []
    offset = 0
    while offset < len(lines):
        part = lines[offset:offset + max_lines]
        result.append(Chunk(chunk.path, chunk.language, chunk.chunk_type, chunk.start_line + offset, chunk.start_line + offset + len(part) - 1, "\n".join(part), chunk.symbol, {"parent_symbol": chunk.symbol, "part": len(result) + 1}))
        if offset + max_lines >= len(lines):
            break
        offset += max_lines - overlap
    return result


def _markdown(path: str, lines: list[str]) -> list[Chunk]:
    starts = [(i, m.group(2)) for i, line in enumerate(lines, 1) if (m := HEADING.match(line))]
    if not starts:
        return []
    result = []
    for index, (start, heading) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        item = _emit(path, "markdown", "SECTION", lines, start, end, heading)
        if item:
            result.extend(_split_large(item))
    return result


def _sql(path: str, lines: list[str]) -> list[Chunk]:
    starts = [i for i, line in enumerate(lines, 1) if SQL_START.match(line)]
    if not starts:
        return []
    result = []
    for index, start in enumerate(starts):
        end = starts[index + 1] - 1 if index + 1 < len(starts) else len(lines)
        symbol_match = re.search(r"(?i)(?:procedure|function|trigger|view|table|into|update|from)\s+([\w.$]+)", lines[start - 1])
        item = _emit(path, "sql", "SQL", lines, start, end, symbol_match.group(1) if symbol_match else None)
        if item:
            result.extend(_split_large(item))
    return result


def _config(path: str, lines: list[str], language: str, pattern: re.Pattern[str]) -> list[Chunk]:
    starts = [(number, match.group(1)) for number, line in enumerate(lines, 1) if (match := pattern.match(line))]
    if not starts:
        return []
    result = []
    if starts[0][0] > 1:
        item = _emit(path, language, "CONFIG", lines, 1, starts[0][0] - 1)
        if item:
            result.append(item)
    for index, (start, key) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        item = _emit(path, language, "CONFIG", lines, start, end, key)
        if item:
            result.extend(_split_large(item))
    return result


def chunk_text(path: str, text: str) -> list[Chunk]:
    suffix = Path(path).suffix.lower()
    lines = text.splitlines(keepends=True)
    chunks: list[Chunk] = []
    if suffix == ".java":
        chunks = _symbol_chunks(path, lines, "java", JAVA_SYMBOL)
    elif suffix == ".py":
        chunks = _symbol_chunks(path, lines, "python", PY_SYMBOL)
    elif suffix in {".js", ".mjs", ".ts"}:
        chunks = _symbol_chunks(path, lines, "javascript", JS_SYMBOL)
    elif suffix == ".md":
        chunks = _markdown(path, lines)
    elif suffix == ".sql":
        chunks = _sql(path, lines)
    elif suffix == ".toml":
        chunks = _config(path, lines, "toml", TOML_SECTION)
    elif suffix == ".json":
        chunks = _config(path, lines, "json", JSON_KEY)
    language = {".json": "json", ".toml": "toml", ".xml": "xml", ".xhtml": "xhtml", ".yml": "yaml", ".yaml": "yaml", ".sh": "shell"}.get(suffix, suffix.lstrip(".") or "text")
    if chunks:
        return chunks
    result = []
    window, overlap = 100, 8
    for start in range(1, len(lines) + 1, window - overlap):
        end = min(len(lines), start + window - 1)
        item = _emit(path, language, "BLOCK", lines, start, end)
        if item:
            result.append(item)
        if end == len(lines):
            break
    return result
