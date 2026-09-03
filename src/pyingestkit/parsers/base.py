from __future__ import annotations

from abc import ABC, abstractmethod

from pyingestkit.artifacts import RawArtifact
from pyingestkit.dataset import Dataset


class Parser(ABC):
    """Structural RAW -> Dataset parser contract."""

    @abstractmethod
    def parse(self, artifact: RawArtifact) -> Dataset:
        raise NotImplementedError
