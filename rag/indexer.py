"""Índice SQLite incremental e separado da telemetria operacional."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .chunkers import chunk_text
from .security import eligible, safe_text

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS documents(
 document_id TEXT PRIMARY KEY, source_type TEXT NOT NULL, repo TEXT NOT NULL,
 path TEXT NOT NULL, language TEXT NOT NULL, content_hash TEXT NOT NULL,
 git_commit TEXT, indexed_at TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS chunks(
 chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(document_id),
 symbol TEXT, chunk_type TEXT NOT NULL, start_line INTEGER NOT NULL, end_line INTEGER NOT NULL,
 text TEXT NOT NULL, text_hash TEXT NOT NULL, token_estimate INTEGER NOT NULL, metadata_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks(document_id);
CREATE UNIQUE INDEX IF NOT EXISTS documents_repo_path_idx ON documents(repo,path);
CREATE TABLE IF NOT EXISTS index_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def digest(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


class RagIndex:
    def __init__(self, database: Path):
        self.database = database.resolve()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.fts5 = self._ensure_fts()

    def _ensure_fts(self) -> bool:
        try:
            self.connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, text, symbol, path)")
            self.connection.execute("INSERT OR REPLACE INTO index_meta VALUES('lexical_backend','FTS5')")
            return True
        except sqlite3.OperationalError:
            self.connection.execute("INSERT OR REPLACE INTO index_meta VALUES('lexical_backend','LIKE_FALLBACK')")
            return False

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "RagIndex":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _files(self, root: Path) -> Iterable[Path]:
        for path in sorted(root.rglob("*")):
            if eligible(path, root):
                yield path

    def index_repo(self, repo: Path, source_type: str = "CODE") -> dict[str, int | str | bool]:
        root = repo.resolve()
        if not root.is_dir():
            raise ValueError(f"repositório inexistente: {root}")
        seen: set[str] = set()
        stats = {"scanned": 0, "indexed": 0, "unchanged": 0, "refused": 0, "removed": 0, "chunks": 0}
        for path in self._files(root):
            relative = path.relative_to(root).as_posix()
            stats["scanned"] += 1
            try:
                raw = path.read_bytes()
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                stats["refused"] += 1
                continue
            if not safe_text(text):
                stats["refused"] += 1
                continue
            seen.add(relative)
            content_hash = digest(raw)
            previous = self.connection.execute("SELECT document_id,content_hash,active FROM documents WHERE repo=? AND path=?", (root.name, relative)).fetchone()
            if previous and previous["content_hash"] == content_hash and previous["active"]:
                stats["unchanged"] += 1
                continue
            document_id = previous["document_id"] if previous else "doc-" + digest(str(root) + ":" + relative)[:24]
            chunks = chunk_text(relative, text)
            with self.connection:
                if previous:
                    self._delete_chunks(document_id)
                self.connection.execute(
                    "INSERT OR REPLACE INTO documents(document_id,source_type,repo,path,language,content_hash,git_commit,indexed_at,active) VALUES(?,?,?,?,?,?,?,?,1)",
                    (document_id, source_type, root.name, relative, path.suffix.lstrip("."), content_hash, None, utc_now()),
                )
                for ordinal, chunk in enumerate(chunks):
                    chunk_id = "chunk-" + digest(f"{document_id}:{chunk.start_line}:{chunk.end_line}:{digest(chunk.text)}")[:24]
                    self.connection.execute(
                        "INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (chunk_id, document_id, chunk.symbol, chunk.chunk_type, chunk.start_line, chunk.end_line, chunk.text, digest(chunk.text), max(1, len(chunk.text) // 4), json.dumps(chunk.metadata, sort_keys=True)),
                    )
                    if self.fts5:
                        self.connection.execute("INSERT INTO chunks_fts(chunk_id,text,symbol,path) VALUES(?,?,?,?)", (chunk_id, chunk.text, chunk.symbol or "", relative))
                    stats["chunks"] += 1
            stats["indexed"] += 1
        active = self.connection.execute("SELECT document_id,path FROM documents WHERE repo=? AND active=1", (root.name,)).fetchall()
        with self.connection:
            for row in active:
                if row["path"] not in seen:
                    self._delete_chunks(row["document_id"])
                    self.connection.execute("UPDATE documents SET active=0,indexed_at=? WHERE document_id=?", (utc_now(), row["document_id"]))
                    stats["removed"] += 1
        return {**stats, "database": str(self.database), "fts5": self.fts5}

    def _delete_chunks(self, document_id: str) -> None:
        if self.fts5:
            ids = [row[0] for row in self.connection.execute("SELECT chunk_id FROM chunks WHERE document_id=?", (document_id,))]
            self.connection.executemany("DELETE FROM chunks_fts WHERE chunk_id=?", ((item,) for item in ids))
        self.connection.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))

    def status(self) -> dict[str, int | str | bool]:
        documents = self.connection.execute("SELECT COUNT(*) FROM documents WHERE active=1").fetchone()[0]
        chunks = self.connection.execute("SELECT COUNT(*) FROM chunks c JOIN documents d ON d.document_id=c.document_id WHERE d.active=1").fetchone()[0]
        return {"database": str(self.database), "documents": documents, "chunks": chunks, "fts5": self.fts5}
