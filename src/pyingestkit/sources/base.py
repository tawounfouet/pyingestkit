from __future__ import annotations

from abc import ABC, abstractmethod

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext


class Source(ABC):
    @abstractmethod
    def fetch(self, context: RunContext) -> RawArtifact:
        raise NotImplementedError
