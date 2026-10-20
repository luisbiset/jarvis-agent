from __future__ import annotations

import re
import unicodedata

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


_SEARCH_STOP_WORDS = frozenset({"a", "ao", "as", "com", "da", "das", "de", "do", "dos", "e", "em", "na", "nas", "no", "nos", "o", "os", "para", "por", "um", "uma"})


def search_terms(text: str) -> tuple[str, ...]:
    """Extract deterministic, auditable terms from a requirement or step query."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").casefold()
    terms = (term for term in re.findall(r"[a-z0-9_./-]+", normalized) if len(term) > 2 and term not in _SEARCH_STOP_WORDS)
    return tuple(dict.fromkeys(terms))
