from __future__ import annotations

from ..gateway import ToolGateway
from ..implementation.models import ImplementationResult
from ..orchestrator.models import ExecutionContext
from .executor import execute
from .models import ValidationResult
from .planner import plan


class ValidationInputError(ValueError):
    pass


class ValidationEngine:
    def execute(self, context: ExecutionContext, gateway: ToolGateway) -> ValidationResult:
        raw = context.artifacts.get("implementation")
        implementation = ImplementationResult.from_dict(raw) if raw is not None else None
        explicit = context.parameters.get("files", [])
        if implementation is None and not context.objective.strip() and not explicit:
            raise ValidationInputError("ImplementationResult ou contexto explícito obrigatório")
        return execute(plan(implementation, list(explicit) if isinstance(explicit, list) else []), gateway)
