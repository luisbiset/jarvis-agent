from __future__ import annotations

from .models import DemandContext, Requirement


OBJECTIVES = {
    "bug": "causa raiz",
    "melhoria": "estado atual versus comportamento esperado",
    "migração": "equivalência e incompatibilidades",
    "refatoração": "comportamentos e acoplamentos",
}


def interpret(text: str, references: tuple[str, ...] = ()) -> DemandContext:
    raw = (text or "").strip()
    lowered = raw.casefold()
    markers = (("bug", "bug"), ("erro", "bug"), ("melhoria", "melhoria"), ("nova funcionalidade", "funcionalidade"), ("migra", "migração"), ("refator", "refatoração"), ("impacto", "análise"))
    demand_type = next((kind for marker, kind in markers if marker in lowered), "desconhecido")
    fragments = [part.strip(" -•\t") for part in raw.replace(";", "\n").splitlines() if part.strip()]
    requirements = tuple(Requirement(f"REQ-{index:02d}", fragment) for index, fragment in enumerate(fragments, 1))
    return DemandContext(
        objective=raw or "Objetivo não informado",
        demand_type=demand_type,
        investigation_objective=OBJECTIVES.get(demand_type, "impacto e estado atual"),
        requirements=requirements,
        references=references,
        ambiguities=() if raw else ("Descrição técnica ausente",),
    )
