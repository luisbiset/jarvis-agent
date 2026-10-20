from __future__ import annotations

from ..gateway import ToolGateway
from ..orchestrator.models import ExecutionContext
from .coverage import evaluate
from .evidence import confirmed
from .executor import execute as execute_plan
from .impact import build as build_impact
from .interpreter import interpret
from .models import AnalysisResult, InvestigationLimits
from .planner import plan
from .strategies import AghuseStrategy, GenericStrategy


class AnalysisEngine:
    def execute(self, context: ExecutionContext, gateway: ToolGateway) -> AnalysisResult:
        references = (context.task_ref,) if context.task_ref else ()
        demand = interpret(context.objective, references)
        investigation_plan = plan(demand, self._strategy(context.project))
        trace = execute_plan(investigation_plan, gateway, self._limits(context))
        impacts = build_impact(trace.findings)
        coverage = evaluate(demand, investigation_plan, trace, len(impacts))
        evidence = confirmed(trace.findings)
        files = tuple(sorted({item["source"]["path"] for item in evidence}))
        observed_metrics = {
            "model": "UNKNOWN/NOT_CONFIRMED",
            "reasoning": "UNKNOWN/NOT_CONFIRMED",
            "attempts": 1,
            "tool_calls": trace.tool_calls,
            "mcp_calls": trace.tool_calls,
            "requirements_total": coverage.requirements_total,
            "steps_planned": len(investigation_plan.steps),
            "steps_executed": len(trace.executed_steps),
            "findings_discovered": len(trace.findings),
            "findings_verified": len(evidence),
            "budget_exhausted": trace.budget_exhausted,
            "tokens": "UNKNOWN/NOT_OBSERVED",
            "credits": "UNKNOWN/NOT_OBSERVED",
        }
        return AnalysisResult(demand, investigation_plan, trace, tuple(trace.findings), impacts, coverage, files, evidence, observed_metrics)

    @staticmethod
    def _strategy(project: str):
        return AghuseStrategy() if project == "aghuse" else GenericStrategy()

    @staticmethod
    def _limits(context: ExecutionContext) -> InvestigationLimits:
        values = context.parameters.get("analysis_limits", {})
        if not isinstance(values, dict):
            return InvestigationLimits()
        aliases = {"max_mcp_calls": "max_tool_calls"}
        allowed = {}
        for key in ("max_steps", "max_findings", "max_tool_calls", "max_mcp_calls"):
            value = values.get(key)
            if isinstance(value, int) and value > 0:
                allowed[aliases.get(key, key)] = value
        return InvestigationLimits(**allowed)
