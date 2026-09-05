from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .uri import ArtifactURI


@dataclass(frozen=True, slots=True)
class RawArtifact:
    artifact_id: str
    source_uri: str
    retrieved_at: datetime
    content_type: str | None
    size_bytes: int
    sha256: str
    path: str
    resolved_url: str | None = None
    status_code: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    storage_uri: str | None = None
    acquisition_mode: str = "LIVE"
    origin_run_id: str | None = None
    origin_artifact_id: str | None = None
    origin_retrieved_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.storage_uri is not None:
            ArtifactURI(self.storage_uri)

    @property
    def location_uri(self) -> ArtifactURI:
        """Canonical persisted location; V0.5 ``path`` remains the local materialization."""

        if self.storage_uri is not None:
            return ArtifactURI(self.storage_uri)
        return ArtifactURI.from_path(self.path)

    @property
    def local_path(self) -> Path:
        return Path(self.path)
