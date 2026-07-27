from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol


class WorkflowMiddleware(Protocol):
    name: str

    def before_step(self, step_name: str, state: dict[str, Any]) -> dict[str, Any]:
        ...

    def after_step(self, step_name: str, result: Any, state: dict[str, Any]) -> Any:
        ...


@dataclass
class ContextBudgetMiddleware:
    """Summarize large workflow state into a compact briefing field."""

    max_chars: int = 12000
    name: str = "context_budget"

    def before_step(self, step_name: str, state: dict[str, Any]) -> dict[str, Any]:
        if len(str(state)) <= self.max_chars:
            return state
        compact_keys = [key for key in state.keys() if not key.startswith("_")]
        state["_middleware_context_summary"] = {
            "reason": "state exceeded middleware budget",
            "step": step_name,
            "keys": compact_keys,
            "chars": len(str(state)),
        }
        return state

    def after_step(self, step_name: str, result: Any, state: dict[str, Any]) -> Any:
        return result


@dataclass
class ToolRiskMiddleware:
    """Expose tool risk contracts to every step without hard-coding prompt text."""

    tool_contracts: list[dict[str, Any]]
    name: str = "tool_risk"

    def before_step(self, step_name: str, state: dict[str, Any]) -> dict[str, Any]:
        state["_tool_contracts"] = self.tool_contracts
        return state

    def after_step(self, step_name: str, result: Any, state: dict[str, Any]) -> Any:
        return result


class MiddlewareChain:
    def __init__(self, middlewares: Optional[list[WorkflowMiddleware]] = None) -> None:
        self.middlewares = middlewares or []

    def before_step(self, step_name: str, state: dict[str, Any]) -> dict[str, Any]:
        for middleware in self.middlewares:
            state = middleware.before_step(step_name, state)
        return state

    def after_step(self, step_name: str, result: Any, state: dict[str, Any]) -> Any:
        for middleware in reversed(self.middlewares):
            result = middleware.after_step(step_name, result, state)
        return result

    def names(self) -> list[str]:
        return [middleware.name for middleware in self.middlewares]
