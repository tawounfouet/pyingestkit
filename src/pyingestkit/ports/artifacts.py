"""Artifact persistence port contracts."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pyingestkit.domain.artifacts import (
    ArtifactReference,
    PutArtifactRequest,
    PutArtifactResult,
)


@runtime_checkable
class ArtifactReader(Protocol):
    """Reader for one durable artifact with integrity verification."""

    @property
    def reference(self) -> ArtifactReference: ...

    def read(self) -> bytes: ...


@runtime_checkable
class ArtifactStore(Protocol):
    """Durable material-evidence store, distinct from publication targets."""

    def put(self, request: PutArtifactRequest) -> PutArtifactResult: ...

    def open(self, reference: ArtifactReference) -> ArtifactReader: ...

    def exists(self, reference: ArtifactReference) -> bool: ...
