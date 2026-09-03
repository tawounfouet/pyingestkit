from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar, overload

from .job_definition import JobDefinition
from .step_definition import StepDefinition

P = ParamSpec("P")
R = TypeVar("R")


@overload
def step(fn: Callable[P, R], /) -> StepDefinition[P, R]: ...


@overload
def step(*, name: str | None = None) -> Callable[[Callable[P, R]], StepDefinition[P, R]]: ...


def step(
    fn: Callable[P, R] | None = None,
    /,
    *,
    name: str | None = None,
) -> StepDefinition[P, R] | Callable[[Callable[P, R]], StepDefinition[P, R]]:
    """Declare a sequential ingestion step.

    V0.1.x deliberately does not expose generic timeout/retry/dependency DAG
    semantics here. Those concerns belong to source-specific primitives or
    future narrowly scoped contracts.
    """

    def decorate(function: Callable[P, R]) -> StepDefinition[P, R]:
        return StepDefinition(function, name or function.__name__)

    return decorate(fn) if fn is not None else decorate


def job(
    *,
    id: str,
    version: str = "0.1.0",
    description: str = "",
    depends_on: tuple[str, ...] = (),
) -> Callable[[Callable[[], None]], JobDefinition]:
    """Declare an ingestion job that compiles to the imperative Job/Pipeline model."""

    def decorate(function: Callable[[], None]) -> JobDefinition:
        return JobDefinition(
            function,
            id=id,
            version=version,
            description=description,
            depends_on=tuple(depends_on),
        )

    return decorate
