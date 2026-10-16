from __future__ import annotations

from ..analysis.models import AnalysisResult


def derive(analysis: AnalysisResult) -> tuple[str, ...]:
    components = [item.get("component") for item in analysis.impact_matrix if item.get("component")]
    return tuple(dict.fromkeys(str(component) for component in components))
