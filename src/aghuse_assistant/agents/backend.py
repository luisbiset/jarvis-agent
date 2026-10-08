"""Backend capability for AGHUse operations."""
from .capabilities import CAPABILITIES
backend = next(item for item in CAPABILITIES if item.name == "backend")