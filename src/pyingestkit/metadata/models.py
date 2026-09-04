from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from pyingestkit.targets import TargetLoadResult


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    job_id: str
    job_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None
    fixture_mode: bool
    parameters: dict[str, Any]
    error: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StepRecord:
    id: int | None
    run_id: str
    position: int
    step_name: str
    status: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    error: str | None
    metrics: dict[str, int | float]


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    run_id: str
    kind: str
    path: str
    source_uri: str
    content_type: str | None
    size_bytes: int
    sha256: str
    created_at: datetime
    resolved_url: str | None = None
    status_code: int | None = None
    etag: str | None = None
    last_modified: str | None = None

    @property
    def retrieved_at(self) -> datetime:
        """Acquisition timestamp; `created_at` remains the storage-compatible column name."""
        return self.created_at


@dataclass(frozen=True, slots=True)
class EventRecord:
    id: int | None
    run_id: str
    job_id: str
    step: str | None
    event_type: str
    level: str
    message: str
    timestamp: datetime
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ValidationRecord:
    id: int | None
    run_id: str
    rule: str
    severity: str
    status: str
    message: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    id: int | None
    run_id: str
    dataset_id: str
    status: str
    candidate_path: str | None
    published_path: str | None
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class TargetLoadRecord:
    """Queryable audit record for one target materialization attempt."""

    load_id: str
    run_id: str
    target_id: str
    dataset_id: str
    dataset_version_id: str | None
    mode: str
    status: str
    destination: str
    rows_input: int
    rows_loaded: int
    rows_verified: int | None
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float | None
    idempotency_action: str | None
    metrics: dict[str, int | float]
    error: str | None
    created_at: datetime

    @classmethod
    def from_result(cls, result: TargetLoadResult, *, created_at: datetime | None = None) -> Self:
        """Build a metadata record without coupling Target implementations to MetadataStore."""

        return cls(
            load_id=result.load_id,
            run_id=result.run_id,
            target_id=result.target_id,
            dataset_id=result.dataset_id,
            dataset_version_id=result.dataset_version_id,
            mode=result.mode.value,
            status=result.status.value,
            destination=result.destination,
            rows_input=result.rows_input,
            rows_loaded=result.rows_loaded,
            rows_verified=result.rows_verified,
            started_at=result.started_at,
            completed_at=result.completed_at,
            duration_seconds=result.duration_seconds,
            idempotency_action=result.idempotency_action,
            metrics=dict(result.metrics),
            error=result.error,
            created_at=created_at or result.completed_at,
        )


@dataclass(frozen=True, slots=True)
class DiffRecord:
    id: int | None
    run_id: str
    step_name: str
    dataset_id: str
    previous_version_id: str
    candidate_fingerprint: str
    added_count: int
    removed_count: int
    changed_count: int
    unchanged_count: int
    entries_truncated: bool
    report_path: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DatasetVersionRecord:
    dataset_id: str
    version_id: str
    fingerprint: str
    snapshot_uri: str
    created_from_run_id: str
    job_id: str
    job_version: str
    source_artifact_id: str | None
    source_raw_sha256: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DatasetVersionRunRecord:
    dataset_id: str
    version_id: str
    run_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PublishedDatasetRecord:
    dataset_id: str
    version_id: str
    published_from_run_id: str
    published_at: datetime


@dataclass(frozen=True, slots=True)
class ReplayRecord:
    run_id: str
    source_run_id: str
    source_job_id: str
    source_job_version: str
    executed_job_version: str
    verification_mode: str
    expected_fingerprint: str | None
    actual_fingerprint: str | None
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ReproducibilityRecord:
    run_id: str
    framework_version: str
    as_of: date | None
    parameters_fingerprint: str
    created_at: datetime
