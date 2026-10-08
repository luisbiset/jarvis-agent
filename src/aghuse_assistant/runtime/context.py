"""Explicit, serializable context passed to an operation."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class OperationContext:
    project: str
    objective: str
    task_ref: str | None = None
    context_refs: tuple[str, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)
