from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ExecutionState(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class ExecutionContext:
    project: str
    operation: str
    objective: str
    task_ref: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_id: str = field(default_factory=lambda: f"codex-{uuid4().hex[:12]}")


@dataclass(frozen=True)
class ExecutionAuthorization:
    mutation_confirmed: bool = False
    external_actions_confirmed: bool = False


@dataclass
class ExecutionResult:
    operation: str
    project: str
    execution_id: str
    state: ExecutionState
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "operation": self.operation,
            "project": self.project,
            "state": self.state.value,
            "summary": self.summary,
            "data": self.data,
            "warnings": self.warnings,
            "evidence": self.evidence,
        }
