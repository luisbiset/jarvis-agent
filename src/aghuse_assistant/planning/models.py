from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PlanResult:
    objective: str
    assumptions: tuple[str, ...]
    steps: tuple[dict[str, Any], ...]
    dependencies: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    validation_plan: tuple[str, ...]
    risks: tuple[dict[str, Any], ...]
    approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PlanResult":
        required = ("objective", "assumptions", "steps", "dependencies", "acceptance_criteria", "validation_plan", "risks")
        if not isinstance(value, dict) or any(key not in value for key in required):
            raise ValueError("invalid PlanResult artifact")
        return cls(str(value["objective"]), tuple(value["assumptions"]), tuple(value["steps"]), tuple(value["dependencies"]), tuple(value["acceptance_criteria"]), tuple(value["validation_plan"]), tuple(value["risks"]), bool(value.get("approved", False)))
