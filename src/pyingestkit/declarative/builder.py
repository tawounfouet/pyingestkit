from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from .invocation import StepInvocation

_CURRENT_BUILDER: ContextVar[PipelineBuilder | None] = ContextVar(
    "pyingestkit_pipeline_builder", default=None
)


@dataclass(slots=True)
class PipelineBuilder:
    """Deterministic sequential pipeline builder used only during ``@job`` build."""

    invocations: list[StepInvocation] = field(default_factory=list)
    _token: Token[PipelineBuilder | None] | None = field(default=None, init=False, repr=False)

    def __enter__(self) -> Self:
        if _CURRENT_BUILDER.get() is not None:
            raise RuntimeError("Nested PyIngestKit declarative job builds are not supported")
        self._token = _CURRENT_BUILDER.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._token is not None:
            _CURRENT_BUILDER.reset(self._token)
            self._token = None

    def add(self, invocation: StepInvocation) -> None:
        self.invocations.append(invocation)


def current_builder() -> PipelineBuilder | None:
    return _CURRENT_BUILDER.get()
