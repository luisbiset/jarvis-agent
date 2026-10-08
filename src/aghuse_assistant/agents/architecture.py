"""Architecture capability for AGHUse operations."""
from .capabilities import CAPABILITIES
architecture = next(item for item in CAPABILITIES if item.name == "architecture")