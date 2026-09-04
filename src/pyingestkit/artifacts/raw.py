from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
    acquisition_mode: str = "LIVE"
    origin_run_id: str | None = None
    origin_artifact_id: str | None = None
    origin_retrieved_at: datetime | None = None
