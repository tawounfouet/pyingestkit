from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .fingerprint import DatasetFingerprint


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    dataset_id: str
    version_id: str
    fingerprint: DatasetFingerprint
    snapshot_uri: str
    created_at: datetime
    created_from_run_id: str
    job_id: str
    job_version: str
    source_artifact_id: str | None = None
    source_raw_sha256: str | None = None
    quality_reports: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PublishedDataset:
    dataset_id: str
    version_id: str
    fingerprint: DatasetFingerprint
    snapshot_uri: str
    published_at: datetime
    published_from_run_id: str
