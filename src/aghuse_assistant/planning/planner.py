from __future__ import annotations

from ..analysis.models import AnalysisResult
from .dependencies import derive
from .models import PlanResult


def build(analysis: AnalysisResult) -> PlanResult:
    steps = tuple({"id": f"STEP-{index:02d}", "description": f"Tratar {item.get('component', 'componente não confirmado')}", "classification": item.get("classification", "UNKNOWN")} for index, item in enumerate(analysis.impact_matrix, 1))
    if not steps:
        steps = ({"id": "STEP-01", "description": f"Implementar {analysis.demand.objective}", "classification": "REQUIRED"},)
    criteria = tuple(f"{requirement.id} atendido: {requirement.text}" for requirement in analysis.demand.requirements)
    validation = tuple(f"Validar {path}" for path in analysis.affected_files) or ("Executar validação direcionada do escopo alterado",)
    return PlanResult(analysis.demand.objective, tuple(analysis.demand.ambiguities), steps, derive(analysis), criteria, validation, ({"severity": "MEDIUM", "description": "Mudanças devem preservar comportamentos confirmados pela análise."},))
