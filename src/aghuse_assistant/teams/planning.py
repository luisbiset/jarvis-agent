from ..gateway import ToolGateway
from ..operations.plan import execute


class PlanningTeam:
    name = "PLANNING"

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def execute(self, context, authorization):
        return execute(context, self.gateway, authorization)
