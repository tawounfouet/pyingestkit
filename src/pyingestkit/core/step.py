from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .context import RunContext


class Step(ABC):
    """A composable, observable unit of ingestion work."""

    name: str | None = None

    @property
    def step_name(self) -> str:
        return self.name or self.__class__.__name__

    @abstractmethod
    def execute(self, context: RunContext, data: Any) -> Any:
        """Execute the step and return data for the next step."""
        raise NotImplementedError
