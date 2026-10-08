"""Technical execution run for one independent operation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_INPUT = "WAITING_INPUT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class OperationRun:
    project: str
    operation: str
    objective: str
    task_ref: str | None = None
    context_refs: list[str] = field(default_factory=list)
    run_id: str = field(default_factory=lambda: f"aghuse-{uuid4().hex[:12]}")
    status: RunStatus = RunStatus.CREATED
    started_at: str | None = None
    finished_at: str | None = None
    result_ref: str | None = None

    def start(self) -> None:
        self.status = RunStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()

    def finish(self, status: RunStatus = RunStatus.SUCCEEDED, result_ref: str | None = None) -> None:
        if status not in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
            raise ValueError("a run can only finish with a terminal status")
        self.status = status
        self.result_ref = result_ref
        self.finished_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict[str, Any]:
        value = dict(self.__dict__)
        value["status"] = self.status.value
        return value
