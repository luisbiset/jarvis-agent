"""Taxonomia determinística e conservadora para artefatos AGHUse."""
from pathlib import Path
import json
import re

def classify(path: str, text: str, source_type: str, model: dict | None = None) -> dict:
    value, suffix = path.casefold(), Path(path).suffix.casefold()
    content = text.casefold()
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
    categories = []
    # Categories are intentionally multi-label: an ON can also be an EJB,
    # and a DAO can be covered by a test. Keep the first label deterministic
    # for consumers that need a single primary classification.
    category_rules = (
        ("XHTML", suffix == ".xhtml"),
        ("SQL", suffix == ".sql" or any(token in value for token in ("/sql/", "\\sql\\", "database", "migration", "ddl"))),
        ("Test", "test" in value or "spec" in value or bool(re.search(r"(?:test|spec)\b", content))),
        ("Security", any(token in value or token in content for token in ("security", "segur", "permission", "perfil", "@rolesallowed", "@permitall"))),
        ("Message", any(token in value or token in content for token in ("message", "mensagem", "resourcebundle", "faces-message"))),
        ("Configuration", any(token in value or token in content for token in ("config", "configuration", "properties", "yaml", "application.yml"))),
        ("Controller", bool(re.search(r"(?:controller|controlador)\b", value + " " + content))),
        ("Service", bool(re.search(r"(?:service|servico|serviço)\b", value + " " + content))),
        ("Facade", bool(re.search(r"facade\b", value + " " + content))),
        ("DAO", bool(re.search(r"(?:dao|dataaccess)\b", value + " " + content))),
        ("Entity", bool(re.search(r"(?:entity|entidade)\b", value + " " + content)) or "@entity" in content),
        ("RN", bool(re.search(r"(?:rn|regradenegocio|regra[_ -]?de[_ -]?neg[oó]cio)\b", value + " " + content))),
        ("ON", bool(re.search(r"(?:on|operacaodenegocio)\b", value + " " + content)) or bool(re.search(r"[a-z0-9]on(?:\.java)?$", value))),
    )
    categories = [label for label, matched in category_rules if matched]
    artifact = "teste" if layer == "testes" else "script_banco" if suffix == ".sql" else "tela" if suffix == ".xhtml" else "documento" if layer == "documentacao" else "codigo"
    if model:
        features = {item.casefold() for item in re.findall(r"[\w.-]{2,}", path)}
        for field in ("layer", "artifact", "category"):
            scores = {label: sum(float(counts.get(term, 0)) for term, counts in model.get("labels", {}).get(field, {}).items() for _ in [0] if term in features) for label in model.get("labels", {}).get(field, {})}
            if scores and max(scores.values()) > 0:
                if field == "layer": layer = max(scores, key=scores.get)
                elif field == "artifact": artifact = max(scores, key=scores.get)
                else:
                    predicted = max(scores, key=scores.get)
                    if predicted not in categories: categories.insert(0, predicted)
    return {"domain": "aghuse", "layer": layer, "artifact": artifact, "category": categories[0] if categories else None, "categories": categories, "source_type": source_type, "technologies": sorted(set(technologies))}
