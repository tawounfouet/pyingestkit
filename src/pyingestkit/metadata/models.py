from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


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
