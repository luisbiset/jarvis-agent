from typing import Protocol, Any


class Retriever(Protocol):
    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]: ...


def retrieve(retriever: Retriever | None, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    if retriever is None or not query.strip():
        return []
    return retriever.search(query, limit=min(limit, 5))
