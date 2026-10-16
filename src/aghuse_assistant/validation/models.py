from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationCheck:
    id: str
    description: str
    target: str


@dataclass(frozen=True)
class ValidationResult:
    checks: tuple[dict[str, Any], ...]
    passed: tuple[dict[str, Any], ...]
    failed: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]
    regressions: tuple[dict[str, Any], ...]
    evidence: tuple[dict[str, Any], ...]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ValidationResult":
        required = ("checks", "passed", "failed", "warnings", "regressions", "evidence", "recommendation")
        if not isinstance(value, dict) or any(key not in value for key in required):
            raise ValueError("invalid ValidationResult artifact")
        return cls(tuple(value["checks"]), tuple(value["passed"]), tuple(value["failed"]), tuple(value["warnings"]), tuple(value["regressions"]), tuple(value["evidence"]), str(value["recommendation"]))
