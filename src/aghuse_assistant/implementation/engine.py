from __future__ import annotations

from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext
from ..planning.models import PlanResult
from .executor import execute
from .models import ImplementationResult


class ImplementationInputError(ValueError):
    pass


class ImplementationEngine:
    def execute(self, context: ExecutionContext, gateway: ToolGateway, authorization: ExecutionAuthorization) -> ImplementationResult:
        if not authorization.mutation_confirmed:
            raise ImplementationInputError("confirmação de mutação obrigatória")
        if context.parameters.get("ambiguous") or context.parameters.get("scope_expanded") or context.parameters.get("external_authorization_required"):
            raise ImplementationInputError("contexto ambíguo, expansão de escopo ou autorização externa pendente")
        raw_plan = context.artifacts.get("plan")
        if raw_plan is not None:
            plan = PlanResult.from_dict(raw_plan)
            if not plan.approved:
                raise ImplementationInputError("plano fornecido deve estar aprovado")
            actions = list(plan.steps)
        elif context.objective.strip():
            actions = [{"id": "DIRECT-01", "description": context.objective, "classification": "REQUIRED"}]
        else:
            raise ImplementationInputError("objetivo ou plano obrigatório")
        return execute(context, gateway, authorization, actions)
