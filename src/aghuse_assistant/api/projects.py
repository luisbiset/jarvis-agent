"""Project resolution API."""
def list_projects() -> list[dict[str, str]]:
    return [{"project_id": "aghuse", "name": "AGHUse"}, {"project_id": "aghuse-assistant", "name": "AGHUse Assistant"}]
