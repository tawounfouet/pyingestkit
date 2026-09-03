from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, ParamSpec, TypeVar

from pyingestkit.core.context import RunContext
from pyingestkit.core.step import Step

from .builder import current_builder
from .invocation import StepInvocation

P = ParamSpec("P")
R = TypeVar("R")


class FunctionStep(Step):
    def __init__(self, invocation: StepInvocation) -> None:
        self.invocation = invocation
        self.name = invocation.step_name

    def execute(self, context: RunContext, data: Any) -> Any:
        return self.invocation.definition.invoke(
            context,
            data,
            self.invocation.args,
            dict(self.invocation.kwargs or {}),
        )


@dataclass
class StepDefinition(Generic[P, R]):
    """Declarative step definition.

    Calling the definition is only valid while a ``@job`` is being built and
    creates a StepInvocation. Use ``.fn(...)`` for direct unit-test execution.
    """

    fn: Callable[P, R]
    name: str

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> StepInvocation:
        builder = current_builder()
        if builder is None:
            raise RuntimeError(
                f"Declarative step '{self.name}' can only be invoked inside a @job build. "
                f"Use {self.name}.fn(...) for direct execution."
            )
        invocation = StepInvocation(self, tuple(args), dict(kwargs))
        builder.add(invocation)
        return invocation

    def to_step(self, invocation: StepInvocation) -> Step:
        return FunctionStep(invocation)

    def invoke(
        self,
        context: RunContext,
        data: Any,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> R:
        signature = inspect.signature(self.fn)
        bound = signature.bind_partial(*args, **kwargs)
        if "context" in signature.parameters and "context" not in bound.arguments:
            kwargs["context"] = context
        if "data" in signature.parameters and "data" not in bound.arguments:
            kwargs["data"] = data
        return self.fn(*args, **kwargs)
