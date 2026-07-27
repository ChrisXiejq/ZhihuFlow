from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

from zhihuflow.storage.memory import MemoryStore
from zhihuflow.runtime.middleware import MiddlewareChain
from zhihuflow.core.schemas import new_id

T = TypeVar("T")


@dataclass
class RuntimeContext:
    trace_id: str
    memory: MemoryStore
    token_budget_chars: int = 12000

    def event(self, event_type: str, payload: Any) -> None:
        self.memory.append_event(self.trace_id, event_type, payload)

    def briefing(self) -> str:
        return self.memory.context_briefing(self.trace_id)


@dataclass
class Step(Generic[T]):
    name: str
    fn: Callable[[RuntimeContext, dict[str, Any]], T]


class JournaledWorkflow:
    """Simple dynamic workflow with journaled replay semantics."""

    def __init__(self, memory: MemoryStore, trace_id: Optional[str] = None, middleware: Optional[MiddlewareChain] = None) -> None:
        self.memory = memory
        self.trace_id = trace_id or new_id("trace")
        self.steps: list[Step[Any]] = []
        self.middleware = middleware or MiddlewareChain()

    def add_step(self, name: str, fn: Callable[[RuntimeContext, dict[str, Any]], Any]) -> "JournaledWorkflow":
        self.steps.append(Step(name=name, fn=fn))
        return self

    def run(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ctx = RuntimeContext(trace_id=self.trace_id, memory=self.memory)
        state: dict[str, Any] = dict(inputs)
        ctx.event("workflow.started", {"steps": [step.name for step in self.steps], "middleware": self.middleware.names()})
        for step in self.steps:
            saved = self.memory.journal_get(self.trace_id, step.name)
            if saved is not None:
                state[step.name] = saved
                ctx.event("workflow.step.replayed", {"step": step.name})
                continue
            state = self.middleware.before_step(step.name, state)
            if len(str(state)) > ctx.token_budget_chars:
                state["_context_briefing"] = ctx.briefing()
                ctx.event("context.offloaded", {"reason": "state exceeded budget", "chars": len(str(state))})
            result = step.fn(ctx, state)
            result = self.middleware.after_step(step.name, result, state)
            self.memory.journal_put(self.trace_id, step.name, result)
            state[step.name] = result
        ctx.event("workflow.completed", {"trace_id": self.trace_id})
        return state
