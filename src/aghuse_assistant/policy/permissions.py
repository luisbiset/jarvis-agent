"""Operation-level permission boundary."""

MUTATING_ACTIONS = {"edit_files", "git_write", "oracle_write"}


def can_execute(operation: str, action: str) -> bool:
    operation = operation.upper()
    if operation not in {"ANALYZE", "PLAN", "IMPLEMENT", "VALIDATE", "MANUTENCAO"}:
        return False
    if action in MUTATING_ACTIONS:
        return operation in {"IMPLEMENT", "MANUTENCAO"}
    return True
