from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .step_definition import StepDefinition


@dataclass(frozen=True, slots=True)
class StepInvocation:
    """One sequential use of a StepDefinition inside a declarative job."""

    definition: "StepDefinition"
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] | None = None

    @property
    def step_name(self) -> str:
        return self.definition.name
