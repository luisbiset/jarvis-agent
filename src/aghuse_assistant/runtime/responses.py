"""Validation and normalization for operation responses."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OPERATIONS = {
    "ANALYZE": ("findings", "impact", "impact_matrix", "coverage", "affected_files", "risks", "recommendations", "evidence"),
    "PLAN": ("objective", "assumptions", "steps", "dependencies", "acceptance_criteria", "validation_plan", "risks"),
    "IMPLEMENT": ("changes", "files_changed", "tests_executed", "tests_passed", "pending_items", "rollback_notes", "approval_required"),
    "VALIDATE": ("checks", "passed", "failed", "warnings", "regressions", "evidence", "recommendation"),
    "MANUTENCAO": ("changes", "files_changed", "tests_executed", "tests_passed", "pending_items", "rollback_notes", "approval_required", "scope", "agent"),
}
CONTRACT_DIR = ROOT / "config" / "contracts" / "responses"
FORBIDDEN = ("AGENTS.md", "api_key", "secret", "credential", "prompt")

class ResponseContractError(ValueError):
    pass

def _validate_schema(value: Any, schema: dict[str, Any], path: str, root: dict[str, Any] | None = None) -> None:
    root = root or schema
    if "$ref" in schema:
        target = schema["$ref"]
        if target.startswith("#/$defs/"):
            schema = root.get("$defs", {}).get(target.split("/", 2)[-1], schema)
    expected = schema.get("type")
    types = expected if isinstance(expected, list) else [expected]
    valid = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "null": value is None,
    }
    if expected and not any(valid.get(item, True) for item in types):
        raise ResponseContractError(f"{path} has invalid type")
    if "const" in schema and value != schema["const"]:
        raise ResponseContractError(f"{path} has invalid value")
    if "enum" in schema and value not in schema["enum"]:
        raise ResponseContractError(f"{path} has invalid value")
    if isinstance(value, dict):
        missing = [key for key in schema.get("required", []) if key not in value]
        if missing: raise ResponseContractError(f"{path} missing fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = [key for key in value if key not in properties]
            if extra: raise ResponseContractError(f"{path} has unexpected fields: {', '.join(extra)}")
        for key, child in properties.items():
            if key in value: _validate_schema(value[key], child, f"{path}.{key}", root)
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value): _validate_schema(item, schema["items"], f"{path}[{index}]", root)
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        raise ResponseContractError(f"{path} is too short")
    if isinstance(value, int) and value < schema.get("minimum", value):
        raise ResponseContractError(f"{path} is below the minimum")

def _load_schema(name: str) -> dict[str, Any]:
    with (CONTRACT_DIR / name).open(encoding="utf-8") as stream:
        return json.load(stream)

def _check(value: Any, operation: str) -> dict[str, Any]:
    if not isinstance(value, dict): raise ResponseContractError("response must be a JSON object")
    if value.get("operation") != operation: raise ResponseContractError("response operation mismatch")
    if value.get("schema_version") != "1.0.0": raise ResponseContractError("unsupported response schema")
    if value.get("status") != "SUCCEEDED": raise ResponseContractError("response status must be SUCCEEDED")
    _validate_schema(value["data"], _load_schema(f"{operation.casefold()}-response.schema.json"), "response.data")
    serialized = json.dumps(value, ensure_ascii=False).casefold()
    if any(token.casefold() in serialized for token in FORBIDDEN): raise ResponseContractError("response contains forbidden metadata")
    return value

def parse_response(raw: str | dict[str, Any], operation: str, run_id: str | None, project_id: str, attempts: int) -> dict[str, Any]:
    try: value = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as exc: raise ResponseContractError(f"invalid JSON: {exc.msg}") from exc
    value = _check(value, operation)
    value = dict(value)
    value.update({"run_id": run_id, "project_id": project_id, "validation": {"schema_valid": True, "attempts": attempts}})
    _validate_schema(value, _load_schema("envelope.schema.json"), "response")
    return value

def deterministic(operation: str, run, attempts: int = 1) -> dict[str, Any]:
    fields = {key: [] if key not in {"impact", "objective", "recommendation", "approval_required", "coverage"} else ("" if key in {"impact", "objective", "recommendation"} else False) for key in OPERATIONS[operation]}
    if operation == "ANALYZE":
        fields["coverage"] = {"analyzed": [], "pending": [], "no_occurrences": [], "not_investigated": [], "searched_terms": [], "limitations": ["No technical investigation was executed."]}
    if operation == "PLAN": fields["objective"] = run.objective
    if operation == "MANUTENCAO":
        fields.update({"scope": "assistant-only", "agent": "aghuse_assistant", "approval_required": True, "rollback_notes": "No changes executed by deterministic shell."})
    return parse_response({"schema_version":"1.0.0", "operation":operation, "run_id":run.run_id, "project_id":run.project, "status":"SUCCEEDED", "summary":"Structured operation result", "data":fields, "warnings":[], "evidence":[], "validation":{"schema_valid":True,"attempts":attempts}}, operation, run.run_id, run.project, attempts)
