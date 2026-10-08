"""Internal agents are selected by operation capability."""
from .capabilities import CAPABILITIES, AgentCapability, select

def allowed_agents(operation: str) -> list[str]:
    return [agent.name for agent in select(operation)]

__all__ = ["CAPABILITIES", "AgentCapability", "select", "allowed_agents"]
from .capabilities import CAPABILITIES, AgentCapability, select

__all__ = ["CAPABILITIES", "AgentCapability", "select"]
