"""Quality capability for AGHUse operations."""
from .capabilities import CAPABILITIES
qa = next(item for item in CAPABILITIES if item.name == "qa")