from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    required: bool = True


@dataclass(frozen=True)
class DemandContext:
    objective: str
    demand_type: str
    investigation_objective: str
    requirements: tuple[Requirement, ...]
    references: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()


@dataclass(frozen=True)
class InvestigationLimits:
    max_steps: int = 12
    max_findings: int = 100
    max_tool_calls: int = 20


@dataclass(frozen=True)
class InvestigationStep:
    id: str
    requirement_id: str
    area: str
    capability: str
    query: str
    preferred_tools: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    stop_condition: str = "evidência verificável ou bloqueio documentado"


@dataclass(frozen=True)
class InvestigationPlan:
    steps: tuple[InvestigationStep, ...]


@dataclass
class InvestigationTrace:
    executed_steps: list[str] = field(default_factory=list)
    searched_terms: list[str] = field(default_factory=list)
    areas_examined: list[str] = field(default_factory=list)
    no_occurrences: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    tool_calls: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    budget_exhausted: bool = False


@dataclass(frozen=True)
class Coverage:
    status: str
    requirements_total: int
    requirements_covered: int
    requirements_pending: tuple[str, ...]
    unsupported_findings: int
    impact_components: int
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisResult:
    demand: DemandContext
    plan: InvestigationPlan
    trace: InvestigationTrace
    findings: tuple[dict[str, Any], ...]
    impact_matrix: tuple[dict[str, Any], ...]
    coverage: Coverage
    affected_files: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AnalysisResult":
        try:
            demand_value = value["demand"]
            demand = DemandContext(
                demand_value["objective"], demand_value["demand_type"], demand_value["investigation_objective"],
                tuple(Requirement(**item) for item in demand_value["requirements"]),
                tuple(demand_value.get("references", ())), tuple(demand_value.get("ambiguities", ())),
            )
            plan_value = value["plan"]
            investigation_plan = InvestigationPlan(tuple(InvestigationStep(
                item["id"], item["requirement_id"], item["area"], item["capability"], item["query"],
                tuple(item.get("preferred_tools", ())), tuple(item.get("depends_on", ())), item.get("stop_condition", "evidência verificável ou bloqueio documentado"),
            ) for item in plan_value["steps"]))
            trace_value = value["trace"]
            trace = InvestigationTrace(**trace_value)
            coverage_value = value["coverage"]
            coverage = Coverage(
                coverage_value["status"], coverage_value["requirements_total"], coverage_value["requirements_covered"],
                tuple(coverage_value["requirements_pending"]), coverage_value["unsupported_findings"],
                coverage_value["impact_components"], tuple(coverage_value.get("limitations", ())),
            )
            return cls(demand, investigation_plan, trace, tuple(value["findings"]), tuple(value["impact_matrix"]), coverage, tuple(value["affected_files"]), tuple(value["evidence"]), dict(value["metrics"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid AnalysisResult artifact") from exc
