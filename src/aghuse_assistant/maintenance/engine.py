from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionAuthorization, ExecutionContext
from .executor import execute
from .models import MaintenanceResult


class MaintenanceInputError(ValueError):
    pass


class MaintenanceEngine:
    def execute(self, context: ExecutionContext, gateway: ToolGateway, authorization: ExecutionAuthorization) -> MaintenanceResult:
        if context.project != "aghuse-assistant":
            raise MaintenanceInputError("manutenção permitida somente para aghuse-assistant")
        if not authorization.mutation_confirmed:
            raise MaintenanceInputError("confirmação de mutação obrigatória")
        return execute(context, gateway, authorization)
