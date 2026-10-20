from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: str
    scope: str
    read_only: bool = True
    confirmation_required: bool = False
    handler: Callable[..., Any] | None = None
    rollback_handler: Callable[..., Any] | None = None


@dataclass(frozen=True)
class ToolResult:
    tool: str
    status: str
    data: Any = None
    warning: str | None = None


class ToolGateway:
    """Single permission boundary for Git, Oracle, Redmine and build/test."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def select(self, *, capability: str | None = None, read_only: bool | None = None) -> tuple[ToolSpec, ...]:
        tools = self._tools.values()
        if capability is not None:
            tools = (tool for tool in tools if tool.capability == capability)
        if read_only is not None:
            tools = (tool for tool in tools if tool.read_only is read_only)
        return tuple(sorted(tools, key=lambda tool: tool.name))

    def invoke(self, name: str, *, confirm: bool = False, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name, "UNAVAILABLE", warning="tool is not registered")
        if tool.confirmation_required and not confirm:
            return ToolResult(name, "WAITING_INPUT", warning="explicit confirmation required")
        if tool.handler is None:
            return ToolResult(name, "UNAVAILABLE", warning="tool handler is not configured")
        try:
            return ToolResult(name, "SUCCEEDED", tool.handler(**kwargs))
        except Exception as exc:
            return ToolResult(name, "FAILED", warning=str(exc))

    def rollback(self, name: str, *, confirm: bool = False, **kwargs: Any) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(name, "UNAVAILABLE", warning="tool is not registered")
        if tool.confirmation_required and not confirm:
            return ToolResult(name, "WAITING_INPUT", warning="explicit confirmation required")
        if tool.rollback_handler is None:
            return ToolResult(name, "UNAVAILABLE", warning="rollback handler is not configured")
        try:
            return ToolResult(name, "SUCCEEDED", tool.rollback_handler(**kwargs))
        except Exception as exc:
            return ToolResult(name, "FAILED", warning=str(exc))
