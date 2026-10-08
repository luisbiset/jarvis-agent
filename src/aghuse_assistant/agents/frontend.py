"""Frontend capability for AGHUse operations."""
from .capabilities import CAPABILITIES
frontend = next(item for item in CAPABILITIES if item.name == "frontend")