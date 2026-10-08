"""Controlled Markdown projections of validated operation envelopes."""
from __future__ import annotations
from typing import Any

UNKNOWN = "UNKNOWN/NOT_CONFIRMED"

def _value(value: Any) -> str:
    if value is None or value == "" or value == []: return UNKNOWN
    if isinstance(value, list): return "\n".join(f"- {_item(item)}" for item in value)
    return str(value)

def _item(value: Any) -> str:
    if isinstance(value, dict):
        if "description" in value:
            return (f"{value.get('severity')}: " if value.get("severity") else "") + str(value["description"])
        if "summary" in value: return str(value["summary"])
        return "; ".join(f"{key}: {item}" for key, item in value.items())
    return str(value)

def _section(title: str, value: Any) -> str: return f"\n### {title}\n\n{_value(value)}\n"

def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows: return UNKNOWN
    result = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    result.extend("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", "<br>") for cell in row) + " |" for row in rows)
    return "\n".join(result)

def _impact_matrix(value: Any) -> str:
    rows = []
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            evidence = "; ".join(_item(entry) for entry in item.get("evidence", []))
            rows.append([item.get("component", UNKNOWN), item.get("role", UNKNOWN), item.get("change", UNKNOWN), item.get("classification", UNKNOWN), item.get("justification", UNKNOWN), evidence or UNKNOWN])
    return _table(["Componente", "Papel identificado", "Alteração", "Classificação", "Justificativa", "Evidência"], rows)

def _coverage(value: Any) -> str:
    if not isinstance(value, dict): return UNKNOWN
    rows = [[label, _value(value.get(key))] for key, label in (("status", "Estado"), ("analyzed", "Referências analisadas"), ("pending", "Pendências"), ("no_occurrences", "Sem ocorrências"), ("not_investigated", "Não investigadas"), ("searched_terms", "Termos pesquisados"), ("limitations", "Limitações"))]
    return _table(["Cobertura", "Resultado"], rows)

def render_analyze(envelope: dict[str, Any]) -> str:
    data = envelope.get("data", {})
    coverage = data.get("coverage", {})
    status = coverage.get("status", UNKNOWN) if isinstance(coverage, dict) else UNKNOWN
    return ("# ANÁLISE TÉCNICA" + _section("Estado", status) + _section("Resumo", envelope.get("summary")) + _section("Objetivo da investigação", data.get("investigation_objective")) + _section("Requisitos", data.get("requirements", envelope.get("evidence"))) + _section("Causa provável", data.get("impact")) + _section("Matriz de impacto", _impact_matrix(data.get("impact_matrix"))) + _section("Cobertura da investigação", _coverage(coverage)) + _section("Achados", data.get("findings")) + _section("Arquivos envolvidos", data.get("affected_files")) + _section("Banco", data.get("database")) + _section("Riscos", data.get("risks")) + _section("Recomendação", data.get("recommendations")) + _section("Evidências", data.get("evidence", envelope.get("evidence"))) + _section("Métricas observadas", data.get("metrics")))

def render_analyze(envelope: dict[str, Any]) -> str:
    data = envelope.get("data", {})
    coverage = data.get("coverage", {})
    status = coverage.get("status", UNKNOWN) if isinstance(coverage, dict) else UNKNOWN
    sections = ["# AN\u00c1LISE T\u00c9CNICA", _section("Estado", status), _section("Resumo", envelope.get("summary")), _section("Objetivo da investiga\u00e7\u00e3o", data.get("investigation_objective")), _section("Perguntas investig\u00e1veis", data.get("questions")), _section("Requisitos", data.get("requirements", envelope.get("evidence"))), _section("Matriz de impacto", _impact_matrix(data.get("impact_matrix"))), _section("Cobertura da investiga\u00e7\u00e3o", _coverage(coverage)), _section("Achados", data.get("findings")), _section("Arquivos envolvidos", data.get("affected_files")), _section("Banco", data.get("database")), _section("Riscos", data.get("risks")), _section("Recomenda\u00e7\u00e3o", data.get("recommendations")), _section("Evid\u00eancias", data.get("evidence", envelope.get("evidence"))), _section("M\u00e9tricas observadas", data.get("metrics"))]
    if data.get("impact") not in (None, "", UNKNOWN):
        sections.insert(5, _section("Impacto", data.get("impact")))
    return "".join(sections)

def render_plan(envelope: dict[str, Any]) -> str:
    data = envelope.get("data", {})
    return "# PLANO TÉCNICO" + _section("Objetivo", data.get("objective")) + _section("Premissas", data.get("assumptions")) + _section("Etapas", data.get("steps")) + _section("Dependências", data.get("dependencies")) + _section("Critérios de aceite", data.get("acceptance_criteria")) + _section("Validação", data.get("validation_plan")) + _section("Riscos", data.get("risks"))

def render_implement(envelope: dict[str, Any]) -> str:
    data = envelope.get("data", {})
    return "# IMPLEMENTAÇÃO CONCLUÍDA" + _section("Resumo", envelope.get("summary")) + _section("Alterações", data.get("changes")) + _section("Arquivos alterados", data.get("files_changed")) + _section("Testes executados", data.get("tests_executed")) + _section("Testes aprovados", data.get("tests_passed")) + _section("Pendências", data.get("pending_items")) + _section("Rollback", data.get("rollback_notes"))

def render_validate(envelope: dict[str, Any]) -> str:
    data = envelope.get("data", {})
    return "# VALIDAÇÃO CONCLUÍDA" + _section("Verificações", data.get("checks")) + _section("Aprovados", data.get("passed")) + _section("Falhas", data.get("failed")) + _section("Regressões", data.get("regressions")) + _section("Avisos", data.get("warnings")) + _section("Recomendação", data.get("recommendation"))

def render_maintenance(envelope: dict[str, Any]) -> str:
    data = envelope.get("data", {})
    return "# MANUTENÇÃO DO AGHUSE ASSISTANT" + _section("Escopo", data.get("scope")) + _section("Agente", data.get("agent")) + _section("Resumo", envelope.get("summary")) + _section("Alterações", data.get("changes")) + _section("Arquivos alterados", data.get("files_changed")) + _section("Testes executados", data.get("tests_executed")) + _section("Testes aprovados", data.get("tests_passed")) + _section("Pendências", data.get("pending_items")) + _section("Rollback", data.get("rollback_notes"))

RENDERERS = {"ANALYZE": render_analyze, "PLAN": render_plan, "IMPLEMENT": render_implement, "VALIDATE": render_validate, "MANUTENCAO": render_maintenance}

def render(envelope: dict[str, Any]) -> str:
    try: return RENDERERS[envelope["operation"]](envelope)
    except KeyError as exc: raise ValueError(f"unsupported response operation: {envelope.get('operation')}") from exc
