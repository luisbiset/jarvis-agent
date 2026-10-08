"""Deterministic, read-only contract primitives for ``/analisar``.

The module deliberately does not access Redmine, a database, or the filesystem.
Adapters can feed observations into these primitives without turning guesses into facts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

TYPES = {"bug", "melhoria", "análise", "funcionalidade", "migração", "refatoração", "desconhecido"}
IMPACT_STATES = {"REQUIRED", "CONDITIONAL", "NO_CHANGE", "UNKNOWN"}
EVIDENCE_TYPES = {"CODE", "DATA", "DOCUMENTATION", "INFERENCE", "ACCESS_LIMITATION"}
CONFIRMED_EVIDENCE_TYPES = {"CODE", "DATA", "DOCUMENTATION"}

@dataclass
class InvestigationLimits:
    max_steps: int = 12
    max_findings: int = 100
    max_mcp_calls: int = 20

@dataclass
class InvestigationTrace:
    searched_terms: list[str] = field(default_factory=list)
    areas_examined: list[str] = field(default_factory=list)
    no_occurrences: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    calls: int = 0
    steps: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class InvestigationQuestion:
    id: str
    requirement_id: str
    question: str
    scope: str = "code"
    stop_condition: str = "evidence specific or documented block"

def investigate_progressively(queries: list[dict[str, Any]], adapter, *, limits: InvestigationLimits | None = None) -> InvestigationTrace:
    """Run bounded read-only adapter queries and preserve failures as limitations.

    ``adapter`` receives one query and returns a list of findings. It must not mutate
    project state; the engine only records its observable result.
    """
    limit = limits or InvestigationLimits()
    trace = InvestigationTrace()
    queue = list(queries)
    seen: set[tuple[str, str, str]] = set()
    while queue:
        query = queue.pop(0)
        key = (str(query.get("area", "")), str(query.get("term", "")), str(query.get("requirement_id", "")))
        if key in seen:
            continue
        seen.add(key)
        if trace.steps >= limit.max_steps or trace.calls >= limit.max_mcp_calls:
            trace.limitations.append("Investigation limit reached before all queries were executed")
            break
        trace.steps += 1
        term = str(query.get("term", "UNKNOWN/NOT_CONFIRMED"))
        area = str(query.get("area", "UNKNOWN/NOT_CONFIRMED"))
        trace.searched_terms.append(term)
        trace.areas_examined.append(area)
        trace.calls += 1
        try:
            result = adapter(query) or []
        except Exception as exc:  # adapter boundary: never turn access failure into a fact
            trace.limitations.append(f"{area}: adapter unavailable ({type(exc).__name__})")
            continue
        if not result:
            trace.no_occurrences.append(f"{area}: {term}")
        retained = result[: max(0, limit.max_findings - len(trace.findings))]
        trace.findings.extend(retained)
        for finding in retained:
            for follow_up in finding.get("follow_up_queries", []) if isinstance(finding, dict) else []:
                if isinstance(follow_up, dict): queue.append(follow_up)
        if len(trace.findings) >= limit.max_findings:
            trace.limitations.append("Finding limit reached before all results were retained")
            break
    return trace

@dataclass
class Requirement:
    id: str
    text: str
    explicit: bool = True
    status: str = "PENDING"

@dataclass
class DemandContext:
    objective: str
    demand_type: str = "desconhecido"
    investigation_objective: str = "impacto e estado atual"
    requirements: list[Requirement] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    ambiguities: list[str] = field(default_factory=list)

def interpret_demand(text: str, *, references: list[str] | None = None) -> DemandContext:
    raw = (text or "").strip()
    lower = raw.casefold()
    pairs = (("bug", "bug"), ("erro", "bug"), ("melhoria", "melhoria"), ("nova funcionalidade", "funcionalidade"),
             ("migra", "migração"), ("refator", "refatoração"), ("impacto", "análise"))
    demand_type = next((kind for marker, kind in pairs if marker in lower), "desconhecido")
    objective = raw or "Objetivo não informado"
    fragments = [part.strip(" -•\t") for part in raw.replace(";", "\n").splitlines() if part.strip()]
    requirements = [Requirement(f"REQ-{i:02d}", part) for i, part in enumerate(fragments, 1)]
    constraints = list(references or [])
    ambiguities = [] if raw else ["Descrição técnica ausente"]
    return DemandContext(objective, demand_type, {"bug": "causa raiz", "melhoria": "atual versus esperado", "migração": "equivalência e incompatibilidades", "refatoração": "comportamentos e acoplamentos"}.get(demand_type, "impacto e estado atual"), requirements, constraints, ambiguities)

def evidence(requirement_id: str, component: str, conclusion: str, *, path: str | None = None, line: int | None = None, kind: str = "CODE", confidence: str = "MEDIUM", limitation: str | None = None) -> dict[str, Any]:
    if kind not in EVIDENCE_TYPES: raise ValueError(f"unsupported evidence type: {kind}")
    item = {"requirement_id": requirement_id, "component": component, "conclusion": conclusion, "type": kind, "confidence": confidence, "source_id": f"{path or 'UNKNOWN/NOT_CONFIRMED'}:{line or 'UNKNOWN'}", "source": {"path": path or "UNKNOWN/NOT_CONFIRMED", "line": line}}
    if limitation: item["limitation"] = limitation
    return item

def impact(component: str, role: str, state: str, justification: str, *, requirement_id: str = "UNKNOWN/NOT_CONFIRMED", evidence_refs: list[str] | None = None) -> dict[str, Any]:
    if state not in IMPACT_STATES: raise ValueError(f"unsupported impact state: {state}")
    return {"component": component, "role": role, "classification": state, "justification": justification, "requirement_id": requirement_id, "evidence_refs": evidence_refs or []}

def validate_coverage(requirements: list[Requirement], findings: list[dict[str, Any]], impacts: list[dict[str, Any]], *, limitations: list[str] | None = None, access_blocked: bool = False) -> dict[str, Any]:
    covered = {item.get("requirement_id") for item in findings if item.get("requirement_id") and _valid_evidence(item)}
    pending = [req.id for req in requirements if req.id not in covered]
    unsupported = [item for item in findings if not _valid_evidence(item) and item.get("type") not in {"INFERENCE", "ACCESS_LIMITATION"}]
    if access_blocked: status = "BLOCKED" if pending else "PARTIAL"
    elif pending or unsupported: status = "PARTIAL"
    else: status = "COMPLETE"
    return {"status": status, "requirements_total": len(requirements), "requirements_covered": len(requirements) - len(pending), "requirements_pending": pending, "unsupported_findings": len(unsupported), "impact_components": len(impacts), "limitations": limitations or []}

def _valid_evidence(item: dict[str, Any]) -> bool:
    source = item.get("source") or {}
    return (item.get("type") in CONFIRMED_EVIDENCE_TYPES
            and item.get("source_id") not in {None, "", "UNKNOWN/NOT_CONFIRMED:UNKNOWN"}
            and source.get("path") not in {None, "", "UNKNOWN/NOT_CONFIRMED"}
            and bool(item.get("conclusion")))

def metrics(*, model: str | None = None, reasoning: str | None = None, attempts: int = 1, mcp_calls: int = 0, duration_ms: int | None = None, agents_used: int = 0, agents_budget: int | None = None, tokens: int | None = None, credits: float | None = None) -> dict[str, Any]:
    return {"model": model or "UNKNOWN/NOT_CONFIRMED", "reasoning": reasoning or "UNKNOWN/NOT_CONFIRMED", "attempts": attempts, "mcp_calls": mcp_calls, "duration_ms": duration_ms if duration_ms is not None else "UNKNOWN/NOT_OBSERVED", "agents": {"used": agents_used, "budget": agents_budget if agents_budget is not None else "UNKNOWN/NOT_CONFIGURED"}, "tokens": tokens if tokens is not None else "UNKNOWN/NOT_OBSERVED", "credits": credits if credits is not None else "UNKNOWN/NOT_OBSERVED"}

def to_dict(context: DemandContext) -> dict[str, Any]:
    value = asdict(context)
    value["requirements"] = [asdict(item) for item in context.requirements]
    return value
