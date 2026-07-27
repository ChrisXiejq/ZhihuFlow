from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: str

    def contract(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "risk": self.risk,
        }


@dataclass
class RegisteredTool:
    definition: ToolDefinition
    handler: Callable[..., Any]


class ToolRegistry:
    """Tool contract registry. Model-facing tools should be registered here first."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, definition: ToolDefinition, handler: Callable[..., Any]) -> None:
        self._tools[definition.name] = RegisteredTool(definition=definition, handler=handler)

    def get(self, name: str) -> RegisteredTool:
        return self._tools[name]

    def contracts(self) -> list[dict[str, Any]]:
        return [tool.definition.contract() for tool in self._tools.values()]


def build_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="trend_search",
            description="Search public AI frontier topic sources and normalize them into TrendCards.",
            input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
            risk="read-only-network",
        ),
        lambda **kwargs: None,
    )
    registry.register(
        ToolDefinition(
            name="research_search",
            description="Search public evidence for a selected topic.",
            input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
            risk="read-only-network",
        ),
        lambda **kwargs: None,
    )
    registry.register(
        ToolDefinition(
            name="artifact_write",
            description="Persist generated briefs, articles, and reports to the local artifact store.",
            input_schema={"type": "object", "required": ["kind", "title"], "properties": {"kind": {"type": "string"}, "title": {"type": "string"}}},
            risk="local-write",
        ),
        lambda **kwargs: None,
    )
    return registry
