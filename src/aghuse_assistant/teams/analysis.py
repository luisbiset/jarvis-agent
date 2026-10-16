from ..operations.analyze import execute
from ..gateway import ToolGateway


class AnalysisTeam:
    name = "ANALYSIS"

    def __init__(self, gateway: ToolGateway) -> None:
        self.gateway = gateway

    def execute(self, context, _authorization):
        return execute(context, self.gateway)
