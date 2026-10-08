"""Canonical operation definitions owned by the new core."""

OPERATIONS = {
    "ANALYZE": {"mutates": False, "result": "AnalysisResult", "required": ("objective",)},
    "PLAN": {"mutates": False, "result": "PlanResult", "required": ("objective",)},
    "IMPLEMENT": {"mutates": True, "result": "ImplementationResult", "required": ("objective",)},
    "VALIDATE": {"mutates": False, "result": "ValidationResult", "required": ("objective",)},
    "MANUTENCAO": {"mutates": True, "result": "MaintenanceResult", "required": ("objective",)},
}

def catalog() -> list[dict]:
    return [{"operation": name, **definition} for name, definition in OPERATIONS.items()]

def validate(operation: str, parameters: dict) -> dict:
    name = operation.upper()
    if name not in OPERATIONS:
        raise ValueError(f"unsupported operation: {operation}")
    clean = {key: value for key, value in parameters.items() if value is not None and str(value).strip()}
    missing = [key for key in OPERATIONS[name]["required"] if not clean.get(key)]
    if missing:
        raise ValueError("missing parameters: " + ", ".join(missing))
    return clean
