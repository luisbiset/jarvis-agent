"""Database capability for AGHUse operations."""
from .capabilities import CAPABILITIES
database = next(item for item in CAPABILITIES if item.name == "database")