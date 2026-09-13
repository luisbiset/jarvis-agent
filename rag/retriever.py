"""Recuperação lexical determinística, ranking e montagem de context pack."""

from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import time
from pathlib import Path
from typing import Any

from .indexer import RagIndex, utc_now
from .models import RetrievalHit

TOKEN = re.compile(r"[A-Za-zÀ-ÿ_][\wÀ-ÿ.$-]{1,}")


def terms(query: str) -> list[str]:
    return list(dict.fromkeys(match.group(0) for match in TOKEN.finditer(query)))


def _fts_query(values: list[str]) -> str:
    return " OR ".join('"' + value.replace('"', '""') + '"' for value in values)


def search(index: RagIndex, query: str, limit: int, path_filter: str | None = None, repo_filter: str | None = None) -> list[RetrievalHit]:
    query_terms = terms(query)
    if not query_terms:
        return []
    params: list[Any] = []
    if index.fts5:
        sql = """SELECT c.*,d.source_type,d.repo,d.path,d.language,d.content_hash,bm25(chunks_fts) raw_score
                 FROM chunks_fts JOIN chunks c ON c.chunk_id=chunks_fts.chunk_id
                 JOIN documents d ON d.document_id=c.document_id
                 WHERE chunks_fts MATCH ? AND d.active=1"""
        params.append(_fts_query(query_terms))
    else:
        clauses = " OR ".join("(c.text LIKE ? OR COALESCE(c.symbol,'') LIKE ? OR d.path LIKE ?)" for _ in query_terms)
        sql = f"""SELECT c.*,d.source_type,d.repo,d.path,d.language,d.content_hash,0.0 raw_score
                  FROM chunks c JOIN documents d ON d.document_id=c.document_id
                  WHERE d.active=1 AND ({clauses})"""
        for value in query_terms:
            params.extend([f"%{value}%"] * 3)
    if path_filter:
        sql += " AND d.path LIKE ?"
        params.append(f"%{path_filter}%")
    if repo_filter:
        sql += " AND d.repo LIKE ?"
        params.append(f"%{repo_filter}%")
    rows = index.connection.execute(sql + " LIMIT ?", (*params, max(limit * 4, limit))).fetchall()
    lowered_query = query.casefold()
    scored: list[RetrievalHit] = []
    for row in rows:
        lexical = 1 / (1 + max(0.0, float(row["raw_score"]))) if index.fts5 else sum(value.casefold() in row["text"].casefold() for value in query_terms) / len(query_terms)
        symbol_bonus = 0.12 if row["symbol"] and row["symbol"].casefold() in lowered_query else 0.0
        path_bonus = 0.08 if any(value.casefold() in row["path"].casefold() for value in query_terms) else 0.0
        final = min(1.0, 0.9 * lexical + symbol_bonus + path_bonus)
        scored.append(RetrievalHit(row["chunk_id"], row["source_type"], row["repo"], row["path"], row["language"], row["chunk_type"], row["symbol"], row["start_line"], row["end_line"], row["content_hash"], round(lexical, 6), 0.0, round(final, 6), row["text"]))
    return sorted(scored, key=lambda hit: (-hit.final_score, hit.path, hit.start_line))[:limit]


def _dedupe_and_budget(hits: list[RetrievalHit], top_k: int, max_tokens: int, max_sources: int) -> tuple[list[RetrievalHit], int, int]:
    selected, hashes, sources = [], set(), set()
    tokens = duplicates = 0
    for hit in hits:
        text_hash = hashlib.sha256(hit.text.encode()).hexdigest()
        if text_hash in hashes:
            duplicates += 1
            continue
        estimate = max(1, math.ceil(len(hit.text) / 4))
        if tokens + estimate > max_tokens or (hit.path not in sources and len(sources) >= max_sources):
            continue
        hashes.add(text_hash); sources.add(hit.path); selected.append(hit); tokens += estimate
        if len(selected) >= top_k:
            break
    return selected, tokens, duplicates


def retrieve(database: Path, query: str, policy: dict[str, Any], context_budget: str, run_id: str | None = None, path_filter: str | None = None, repo_filter: str | None = None) -> dict[str, Any]:
    started = time.monotonic()
    budget = policy["budgets"][context_budget]
    with RagIndex(database) as index:
        candidates = search(index, query, budget["candidate_k"], path_filter, repo_filter)
    selected, estimated_tokens, duplicates = _dedupe_and_budget(candidates, budget["top_k"], budget["max_tokens"], budget.get("max_sources", budget["top_k"]))
    query_id = "ragq-" + secrets.token_hex(8)
    filters_hash = hashlib.sha256(json.dumps({"path": path_filter, "repo": repo_filter}, sort_keys=True).encode()).hexdigest()
    return {
        "schema_version": "1.0.0", "run_id": run_id, "query_id": query_id,
        "query_hash": hashlib.sha256(query.encode()).hexdigest(), "filters_hash": filters_hash, "created_at": utc_now(),
        "context_budget": context_budget, "retrieval_mode": "LEXICAL_ONLY",
        "candidates": len(candidates), "hits": [hit.as_dict() for hit in selected],
        "estimated_tokens": estimated_tokens, "duplicate_chunks_removed": duplicates,
        "latency_ms": round((time.monotonic() - started) * 1000),
    }


def write_context_pack(destination: Path, payload: dict[str, Any]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination
