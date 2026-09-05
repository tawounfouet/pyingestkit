from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .uri import ArtifactURI


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """Durable run-artifact identity plus its local materialization metadata."""

    relative_path: str
    path: str
    storage_uri: str
    content_type: str | None
    size_bytes: int
    sha256: str

    @property
    def local_path(self) -> Path:
        return Path(self.path)

    @property
    def location_uri(self) -> ArtifactURI:
        return ArtifactURI(self.storage_uri)
