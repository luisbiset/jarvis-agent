from ..gateway import ToolGateway
from ..operations.implement import execute


class DevelopmentTeam:
    name = "DEVELOPMENT"

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def execute(self, context, authorization):
        return execute(context, self.gateway, authorization)
