"""Taxonomia determinística e conservadora para artefatos AGHUse."""
from pathlib import Path
import json
import re

def classify(path: str, text: str, source_type: str, model: dict | None = None) -> dict:
    value, suffix = path.casefold(), Path(path).suffix.casefold()
    if suffix in {".xhtml", ".xml", ".js", ".ts"} or "webapp" in value: layer = "frontend"
    elif suffix == ".sql" or any(x in value for x in ("database", "banco", "migration", "ddl")): layer = "banco"
    elif "test" in value or "spec" in value: layer = "testes"
    elif any(x in value for x in ("security", "segur", "permission", "perfil")): layer = "seguranca"
    elif suffix in {".java", ".py", ".js", ".mjs", ".ts"}: layer = "backend"
    else: layer = "documentacao"
    technologies = []
    if suffix == ".java": technologies += ["java", "ejb"]
    if suffix == ".xhtml" or "primefaces" in text.casefold(): technologies += ["jsf", "primefaces"]
    if suffix == ".sql": technologies.append("sql")
    artifact = "teste" if layer == "testes" else "script_banco" if suffix == ".sql" else "tela" if suffix == ".xhtml" else "documento" if layer == "documentacao" else "codigo"
    if model:
        features = {item.casefold() for item in re.findall(r"[\w.-]{2,}", path)}
        for field in ("layer", "artifact"):
            scores = {label: sum(float(counts.get(term, 0)) for term, counts in model.get("labels", {}).get(field, {}).items() for _ in [0] if term in features) for label in model.get("labels", {}).get(field, {})}
            if scores and max(scores.values()) > 0:
                if field == "layer": layer = max(scores, key=scores.get)
                else: artifact = max(scores, key=scores.get)
    return {"domain": "aghuse", "layer": layer, "artifact": artifact, "source_type": source_type, "technologies": sorted(set(technologies))}
