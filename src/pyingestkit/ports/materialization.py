"""Dataset materialization port for PyIngestKit V2."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pyingestkit.domain.materialization import (
    MaterializationRequest,
    MaterializationResult,
)


@runtime_checkable
class DatasetMaterializer(Protocol):
    """Provider-neutral port that materializes immutable dataset versions."""

    @property
    def materializer_id(self) -> str: ...

    def materialize(self, request: MaterializationRequest) -> MaterializationResult: ...
