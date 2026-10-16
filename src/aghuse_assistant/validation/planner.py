from __future__ import annotations

from ..implementation.models import ImplementationResult
from .models import ValidationCheck


def plan(implementation: ImplementationResult | None, explicit: list[str]) -> tuple[ValidationCheck, ...]:
    targets = list(implementation.files_changed) if implementation else explicit
    if not targets:
        targets = ["escopo informado"]
    return tuple(ValidationCheck(f"CHECK-{index:02d}", f"Validar {target}", target) for index, target in enumerate(targets, 1))
