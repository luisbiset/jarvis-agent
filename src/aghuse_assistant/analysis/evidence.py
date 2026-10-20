from __future__ import annotations

from typing import Any

EVIDENCE_TYPES = {"CODE", "DATA", "DOCUMENTATION", "INFERENCE", "ACCESS_LIMITATION"}
CONFIRMED_TYPES = {"CODE", "DATA", "DOCUMENTATION"}
SEMANTIC_CLASSIFICATIONS = {"REQUIRED", "CONDITIONAL", "NO_CHANGE"}


def normalize(item: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    value = dict(item)
    value.setdefault("requirement_id", requirement_id)
    value.setdefault("type", "INFERENCE")
    value.setdefault("confidence", "MEDIUM")
    value.setdefault("matched_terms", ())
    source = value.get("source") if isinstance(value.get("source"), dict) else {}
    source = {"path": source.get("path", "UNKNOWN/NOT_CONFIRMED"), "line": source.get("line")}
    value["source"] = source
    value.setdefault("source_id", f"{source['path']}:{source['line'] or 'UNKNOWN'}")
    return value


def validate(item: dict[str, Any]) -> tuple[bool, str]:
    """Validate the minimum provenance required for a usable tool finding."""
    source = item.get("source")
    path = source.get("path") if isinstance(source, dict) else None
    line = source.get("line") if isinstance(source, dict) else None
    matched_terms = item.get("matched_terms")
    if not isinstance(item.get("requirement_id"), str) or not item["requirement_id"].strip():
        return False, "requirement_id ausente"
    if not isinstance(item.get("component"), str) or not item["component"].strip():
        return False, "component ausente"
    if item.get("classification") not in SEMANTIC_CLASSIFICATIONS:
        return False, "classification semântica inválida"
    if item.get("type") not in CONFIRMED_TYPES:
        return False, "tipo de evidência não verificável"
    if not isinstance(item.get("conclusion"), str) or not item["conclusion"].strip():
        return False, "conclusion ausente"
    if not isinstance(path, str) or not path.strip() or path == "UNKNOWN/NOT_CONFIRMED":
        return False, "caminho de origem ausente"
    if path.startswith(("/", "\\")) or ".." in path.replace("\\", "/").split("/"):
        return False, "caminho de origem fora do workspace"
    if not isinstance(line, int) or isinstance(line, bool) or line <= 0:
        return False, "linha de origem inválida"
    if not isinstance(item.get("source_id"), str) or not item["source_id"].strip():
        return False, "source_id ausente"
    if not isinstance(matched_terms, (list, tuple)) or not matched_terms or not all(isinstance(term, str) and term.strip() for term in matched_terms):
        return False, "termos correspondentes ausentes"
    return True, ""


def is_confirmed(item: dict[str, Any]) -> bool:
    valid, _ = validate(item)
    return valid


def confirmed(findings: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    return tuple(item for item in findings if is_confirmed(item))
