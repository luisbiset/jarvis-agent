from ..gateway import ToolGateway
from ..operations.maintenance import execute


class MaintenanceTeam:
    name = "MAINTENANCE"

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def execute(self, context, authorization):
        return execute(context, self.gateway, authorization)
