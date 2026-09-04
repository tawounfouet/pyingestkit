from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self

from .capabilities import TargetCapabilities
from .models import TargetLoadRequest, TargetLoadResult


class Target(ABC):
    """Destination contract for materializing framework-owned Datasets.

    The public contract is intentionally high-level. Transaction primitives such as
    prepare/commit/rollback remain backend implementation details so a PostgreSQL
    transaction model is not accidentally imposed on future target types.
    """

    @property
    @abstractmethod
    def target_id(self) -> str:
        """Stable logical identity that never contains credentials."""

    @property
    @abstractmethod
    def capabilities(self) -> TargetCapabilities:
        """Explicit features implemented by this target instance."""

    @abstractmethod
    def open(self) -> Self:
        """Validate that the target can be reached and is ready for loads."""

    @abstractmethod
    def load(self, request: TargetLoadRequest) -> TargetLoadResult:
        """Materialize one Dataset according to an explicit load request."""

    @abstractmethod
    def close(self) -> None:
        """Release target resources. Implementations must make close idempotent."""

    def __enter__(self) -> Self:
        return self.open()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback
        self.close()
