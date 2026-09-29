"""Recuperação lexical determinística, ranking e montagem de context pack."""

from __future__ import annotations

import hashlib
import json
import math
import re
import secrets
import time
import unicodedata
from pathlib import Path
from typing import Any

from .indexer import RagIndex, utc_now
from .models import RetrievalHit

TOKEN = re.compile(r"[A-Za-zÀ-ÿ_][\wÀ-ÿ.$-]{1,}")


def _fold(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(char))


def terms(query: str) -> list[str]:
    return list(dict.fromkeys(_fold(match.group(0)) for match in TOKEN.finditer(query)))


def _fts_query(values: list[str]) -> str:
    return " OR ".join('"' + value.replace('"', '""') + '"' for value in values)


def load_reranker(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    model = json.loads(path.read_text(encoding="utf-8"))
    if model.get("schema_version") != "1.0.0" or model.get("method") != "term_log_odds":
        raise ValueError("reranker incompatível")
    return model


def reranker_score(model: dict[str, Any], query: str, hit: RetrievalHit) -> float:
    values = set(_fold(query).split()) | {"path:" + value for value in _fold(hit.path).replace("/", " ").split()} | {"symbol:" + value for value in _fold(hit.symbol or "").split()}
    weights = model.get("weights", {})
    return sum(float(weights.get(value, 0.0)) for value in values)


def search(index: RagIndex, query: str, limit: int, path_filter: str | None = None, repo_filter: str | None = None, branch_filter: str | None = None, source_type_filter: str | None = None, taxonomy: dict[str, str] | None = None, reranker: dict[str, Any] | None = None) -> list[RetrievalHit]:
    raw_terms = list(dict.fromkeys(match.group(0) for match in TOKEN.finditer(query)))
    query_terms = [_fold(value) for value in raw_terms]
    if not query_terms:
        return []
    params: list[Any] = []
    if index.fts5:
        sql = """SELECT c.*,d.source_type,d.repo,d.path,d.language,d.content_hash,bm25(chunks_fts) raw_score
                 FROM chunks_fts JOIN chunks c ON c.chunk_id=chunks_fts.chunk_id
                 JOIN documents d ON d.document_id=c.document_id
                 WHERE chunks_fts MATCH ? AND d.active=1"""
        params.append(_fts_query(raw_terms))
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
    if branch_filter:
        sql += " AND d.git_branch LIKE ?"
        params.append(f"%{branch_filter}%")
    if source_type_filter:
        sql += " AND d.source_type = ?"
        params.append(source_type_filter)
    for key, value in (taxonomy or {}).items():
        if key not in {"domain", "layer", "artifact", "category"}:
            raise ValueError(f"filtro taxonômico inválido: {key}")
        sql += " AND json_extract(c.metadata_json, ?) = ?"
        params.extend([f"$.{key}", value])
    rows = index.connection.execute(sql + " LIMIT ?", (*params, max(limit * 4, limit))).fetchall()
    lowered_query = _fold(query)
    phrase = _fold(" ".join(query_terms))
    scored: list[RetrievalHit] = []
    for row in rows:
        text = _fold(row["text"])
        symbol = _fold(row["symbol"] or "")
        path = _fold(row["path"])
        searchable = f"{text} {symbol} {path}"
        coverage = sum(term in searchable for term in query_terms) / len(query_terms)
        exact = 1.0 if phrase and phrase in text else 0.0
        symbol_bonus = 0.22 if symbol and symbol in lowered_query else 0.0
        path_bonus = 0.24 if any(value in path for value in query_terms) else 0.0
        path_exact_bonus = 0.18 if any(value.replace("_", "-") in path for value in query_terms) else 0.0
        # SQLite FTS5 bm25 is lower-is-better and may be negative; normalize it
        # relative to the candidate set instead of collapsing all negatives to 1.
        raw = float(row["raw_score"])
        lexical = 1 / (1 + math.exp(min(20.0, max(-20.0, raw)))) if index.fts5 else coverage
        final = min(1.0, 0.48 * coverage + 0.22 * lexical + 0.12 * exact + symbol_bonus + path_bonus + path_exact_bonus)
        metadata = json.loads(row["metadata_json"] or "{}")
        reasons = []
        if any(term in symbol for term in query_terms): reasons.append("query_term_in_symbol")
        if any(term in path for term in query_terms): reasons.append("query_term_in_path")
        if any(term in text for term in query_terms): reasons.append("query_term_in_content")
        if exact: reasons.append("exact_phrase_in_content")
        if taxonomy: reasons.append("taxonomy_filter_match")
        if reranker and reranker_score(reranker, query, RetrievalHit(row["chunk_id"], row["source_type"], row["repo"], row["path"], row["language"], row["chunk_type"], row["symbol"], row["start_line"], row["end_line"], row["content_hash"], 0.0, 0.0, 0.0, row["text"])) != 0: reasons.append("reranker_weight_match")
        scored.append(RetrievalHit(row["chunk_id"], row["source_type"], row["repo"], row["path"], row["language"], row["chunk_type"], row["symbol"], row["start_line"], row["end_line"], row["content_hash"], round(lexical, 6), 0.0, round(final, 6), row["text"], metadata, reasons, "selected_by_ranked_relevance"))
    ordered = sorted(scored, key=lambda hit: (-hit.final_score, hit.path, hit.start_line))
    if reranker:
        ordered.sort(key=lambda hit: (-reranker_score(reranker, query, hit), -hit.final_score, hit.path, hit.start_line))
    return ordered[:limit]


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


def retrieve(database: Path, query: str, policy: dict[str, Any], context_budget: str, run_id: str | None = None, path_filter: str | None = None, repo_filter: str | None = None, branch_filter: str | None = None, source_type_filter: str | None = None, taxonomy: dict[str, str] | None = None, reranker_path: Path | None = None) -> dict[str, Any]:
    started = time.monotonic()
    budget = policy["budgets"][context_budget]
    reranker = load_reranker(reranker_path)
    with RagIndex(database) as index:
        candidates = search(index, query, budget["candidate_k"], path_filter, repo_filter, branch_filter, source_type_filter, taxonomy, reranker)
    selected, estimated_tokens, duplicates = _dedupe_and_budget(candidates, budget["top_k"], budget["max_tokens"], budget.get("max_sources", budget["top_k"]))
    query_id = "ragq-" + secrets.token_hex(8)
    filters_hash = hashlib.sha256(json.dumps({"path": path_filter, "repo": repo_filter, "branch": branch_filter, "source_type": source_type_filter, "taxonomy": taxonomy, "reranker": str(reranker_path) if reranker_path else None}, sort_keys=True).encode()).hexdigest()
    return {
        "schema_version": "1.0.0", "run_id": run_id, "query_id": query_id,
        "query_hash": hashlib.sha256(query.encode()).hexdigest(), "filters_hash": filters_hash, "created_at": utc_now(),
        "context_budget": context_budget, "retrieval_mode": "LEXICAL_RERANKED" if reranker else "LEXICAL_ONLY",
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
