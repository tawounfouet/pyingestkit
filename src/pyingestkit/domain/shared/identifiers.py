"""Typed identifiers used by the PyIngestKit V2 domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Identifier:
    """Immutable UUID-backed domain identifier."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("Identifier value must be a UUID.")

    @classmethod
    def new(cls) -> Self:
        """Create a new identifier of the concrete identifier type."""
        return cls(uuid4())

    @classmethod
    def parse(cls, value: str) -> Self:
        """Parse a UUID string into the concrete identifier type."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Identifier text must be a non-empty string.")
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class IngestionRunId(Identifier):
    """Identity of one semantic PyIngestKit ingestion execution."""


@dataclass(frozen=True, slots=True)
class CorrelationId(Identifier):
    """Identity grouping related work without replacing native execution IDs."""
