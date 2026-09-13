"""Modelos estáveis compartilhados pelo indexador e pelo retriever."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Chunk:
    path: str
    language: str
    chunk_type: str
    start_line: int
    end_line: int
    text: str
    symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    source_type: str
    repo: str
    path: str
    language: str
    chunk_type: str
    symbol: str | None
    start_line: int
    end_line: int
    content_hash: str
    lexical_score: float
    semantic_score: float
    final_score: float
    text: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class VectorStore(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def delete_document(self, document_id: str) -> None: ...

    def search(self, query_vector: list[float], limit: int, filters: dict[str, Any] | None = None) -> list[tuple[str, float]]: ...
