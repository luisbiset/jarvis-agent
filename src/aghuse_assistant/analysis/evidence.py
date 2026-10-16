from __future__ import annotations

from typing import Any

EVIDENCE_TYPES = {"CODE", "DATA", "DOCUMENTATION", "INFERENCE", "ACCESS_LIMITATION"}
CONFIRMED_TYPES = {"CODE", "DATA", "DOCUMENTATION"}


def normalize(item: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    value = dict(item)
    value.setdefault("requirement_id", requirement_id)
    value.setdefault("type", "INFERENCE")
    value.setdefault("confidence", "MEDIUM")
    source = value.get("source") if isinstance(value.get("source"), dict) else {}
    source = {"path": source.get("path", "UNKNOWN/NOT_CONFIRMED"), "line": source.get("line")}
    value["source"] = source
    value.setdefault("source_id", f"{source['path']}:{source['line'] or 'UNKNOWN'}")
    return value


def is_confirmed(item: dict[str, Any]) -> bool:
    source = item.get("source") or {}
    return (
        item.get("type") in CONFIRMED_TYPES
        and item.get("type") in EVIDENCE_TYPES
        and bool(item.get("requirement_id"))
        and bool(item.get("conclusion"))
        and item.get("source_id") not in {None, "", "UNKNOWN/NOT_CONFIRMED:UNKNOWN"}
        and source.get("path") not in {None, "", "UNKNOWN/NOT_CONFIRMED"}
    )


def confirmed(findings: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    return tuple(item for item in findings if is_confirmed(item))
