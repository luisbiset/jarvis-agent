"""The four independent first-class operations."""
from .catalog import OPERATIONS, catalog, validate

ANALYZE, PLAN, IMPLEMENT, VALIDATE, MANUTENCAO = OPERATIONS

__all__ = ["OPERATIONS", "catalog", "validate", "ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE", "MANUTENCAO"]
