from __future__ import annotations

from typing import Any

ALLOWED_STATES = {"REQUIRED", "CONDITIONAL", "NO_CHANGE", "UNKNOWN"}


def build(findings: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    matrix = []
    for finding in findings:
        state = finding.get("classification")
        if not finding.get("component") or state not in ALLOWED_STATES:
            continue
        matrix.append({
            "component": finding["component"],
            "role": finding.get("role", "UNKNOWN/NOT_CONFIRMED"),
            "classification": state,
            "change": finding.get("change", "UNKNOWN/NOT_CONFIRMED"),
            "justification": finding.get("justification", finding.get("conclusion", "UNKNOWN/NOT_CONFIRMED")),
            "evidence": finding.get("evidence", []),
            "status": finding.get("status", "PARTIAL"),
        })
    return tuple(matrix)
