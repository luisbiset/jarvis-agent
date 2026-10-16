from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MaintenanceResult:
    changes: tuple[dict[str, Any], ...]
    files_changed: tuple[str, ...]
    tests_executed: tuple[str, ...]
    tests_passed: tuple[str, ...]
    pending_items: tuple[str, ...]
    rollback_notes: str
    approval_required: bool = False
    scope: str = "assistant-only"
    agent: str = "aghuse_assistant"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MaintenanceResult":
        required = ("changes", "files_changed", "tests_executed", "tests_passed", "pending_items", "rollback_notes", "approval_required", "scope", "agent")
        if not isinstance(value, dict) or any(key not in value for key in required) or value["scope"] != "assistant-only" or value["agent"] != "aghuse_assistant":
            raise ValueError("invalid MaintenanceResult artifact")
        return cls(tuple(value["changes"]), tuple(value["files_changed"]), tuple(value["tests_executed"]), tuple(value["tests_passed"]), tuple(value["pending_items"]), str(value["rollback_notes"]), bool(value["approval_required"]))
