"""Stable result envelope for operations."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class OperationResult:
    operation_id: str
    project_id: str
    run_id: str | None
    status: str
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=lambda: {"schema_valid": True, "attempts": 1})

    @property
    def metadata(self) -> dict[str, Any]:
        """Compatibility view for legacy callers; public output uses data."""
        return self.data

    def as_dict(self) -> dict[str, Any]:
        return {"schema_version": "1.0.0", "operation": self.operation_id, "run_id": self.run_id,
                "project_id": self.project_id, "status": self.status, "summary": self.summary,
                "data": self.data, "warnings": self.warnings, "evidence": self.evidence,
                "validation": self.validation}
