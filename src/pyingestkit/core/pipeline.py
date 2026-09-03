from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .step import Step


@dataclass(frozen=True, slots=True)
class Pipeline:
    steps: tuple[Step, ...]

    def __init__(self, steps: Iterable[Step]) -> None:
        object.__setattr__(self, "steps", tuple(steps))

    def __iter__(self) -> Iterator[Step]:
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)
