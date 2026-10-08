"""Passive capability registry for MCP/tool adapters."""
from dataclasses import dataclass
from typing import Callable, Any


@dataclass(frozen=True)
class Tool:
    name: str
    handler: Callable[..., Any]
    read_only: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
