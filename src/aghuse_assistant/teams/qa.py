from ..operations.validate import execute
from ..gateway import ToolGateway


class QATeam:
    name = "QA"

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def execute(self, context, authorization):
        return execute(context, self.gateway, authorization)
