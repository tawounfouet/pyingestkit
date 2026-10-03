"""Canonical non-executable V1 semantic export for LOT-18."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Self

from pyingestkit.metadata.models import (
    ArtifactRecord,
    DatasetVersionRecord,
    PublishedDatasetRecord,
    ReplayRecord,
)

_EXPORT_SCHEMA = "pyingestkit.v1-semantic-export"
_EXPORT_VERSION = "1"


@dataclass(frozen=True, slots=True)
class LegacyArtifactSnapshot:
    artifact_id: str
    run_id: str
    kind: str
    path: str
    source_uri: str
    content_type: str | None
    size_bytes: int
    sha256: str
    created_at: str
    resolved_url: str | None
    status_code: int | None
    etag: str | None
    last_modified: str | None
    storage_uri: str | None


@dataclass(frozen=True, slots=True)
class LegacyDatasetVersionSnapshot:
    dataset_id: str
    version_id: str
    fingerprint: str
    snapshot_uri: str
    created_from_run_id: str
    job_id: str
    job_version: str
    source_artifact_id: str | None
    source_raw_sha256: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class LegacyPublishedDatasetSnapshot:
    dataset_id: str
    version_id: str
    published_from_run_id: str
    published_at: str


@dataclass(frozen=True, slots=True)
class LegacyReplaySnapshot:
    run_id: str
    source_run_id: str
    source_job_id: str
    source_job_version: str
    executed_job_version: str
    verification_mode: str
    expected_fingerprint: str | None
    actual_fingerprint: str | None
    status: str
    created_at: str


@dataclass(frozen=True, slots=True)
class V1SemanticExport:
    """Versioned semantic export independent from V1 physical metadata tables."""

    source_version: str
    artifacts: tuple[LegacyArtifactSnapshot, ...] = ()
    dataset_versions: tuple[LegacyDatasetVersionSnapshot, ...] = ()
    publications: tuple[LegacyPublishedDatasetSnapshot, ...] = ()
    replays: tuple[LegacyReplaySnapshot, ...] = ()

    @classmethod
    def from_public_records(
        cls,
        *,
        source_version: str,
        artifacts: tuple[ArtifactRecord, ...] = (),
        dataset_versions: tuple[DatasetVersionRecord, ...] = (),
        publications: tuple[PublishedDatasetRecord, ...] = (),
        replays: tuple[ReplayRecord, ...] = (),
    ) -> Self:
        if not isinstance(source_version, str) or not source_version.strip():
            raise ValueError("V1SemanticExport source_version must be non-blank.")

        return cls(
            source_version=source_version,
            artifacts=tuple(
                LegacyArtifactSnapshot(
                    artifact_id=item.artifact_id,
                    run_id=item.run_id,
                    kind=item.kind,
                    path=item.path,
                    source_uri=item.source_uri,
                    content_type=item.content_type,
                    size_bytes=item.size_bytes,
                    sha256=item.sha256,
                    created_at=_datetime_text(item.created_at),
                    resolved_url=item.resolved_url,
                    status_code=item.status_code,
                    etag=item.etag,
                    last_modified=item.last_modified,
                    storage_uri=item.storage_uri,
                )
                for item in artifacts
            ),
            dataset_versions=tuple(
                LegacyDatasetVersionSnapshot(
                    dataset_id=item.dataset_id,
                    version_id=item.version_id,
                    fingerprint=item.fingerprint,
                    snapshot_uri=item.snapshot_uri,
                    created_from_run_id=item.created_from_run_id,
                    job_id=item.job_id,
                    job_version=item.job_version,
                    source_artifact_id=item.source_artifact_id,
                    source_raw_sha256=item.source_raw_sha256,
                    created_at=_datetime_text(item.created_at),
                )
                for item in dataset_versions
            ),
            publications=tuple(
                LegacyPublishedDatasetSnapshot(
                    dataset_id=item.dataset_id,
                    version_id=item.version_id,
                    published_from_run_id=item.published_from_run_id,
                    published_at=_datetime_text(item.published_at),
                )
                for item in publications
            ),
            replays=tuple(
                LegacyReplaySnapshot(
                    run_id=item.run_id,
                    source_run_id=item.source_run_id,
                    source_job_id=item.source_job_id,
                    source_job_version=item.source_job_version,
                    executed_job_version=item.executed_job_version,
                    verification_mode=item.verification_mode,
                    expected_fingerprint=item.expected_fingerprint,
                    actual_fingerprint=item.actual_fingerprint,
                    status=item.status,
                    created_at=_datetime_text(item.created_at),
                )
                for item in replays
            ),
        )

    def to_bytes(self) -> bytes:
        payload = {
            "schema": _EXPORT_SCHEMA,
            "schema_version": _EXPORT_VERSION,
            "source_version": self.source_version,
            "artifacts": [asdict(item) for item in self.artifacts],
            "dataset_versions": [asdict(item) for item in self.dataset_versions],
            "publications": [asdict(item) for item in self.publications],
            "replays": [asdict(item) for item in self.replays],
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    @classmethod
    def from_bytes(cls, content: bytes) -> Self:
        if not isinstance(content, bytes):
            raise TypeError("V1SemanticExport.from_bytes expects bytes.")
        try:
            raw = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("V1 semantic export must be valid UTF-8 JSON.") from exc
        if not isinstance(raw, dict):
            raise ValueError("V1 semantic export root must be a JSON object.")
        expected = {
            "schema",
            "schema_version",
            "source_version",
            "artifacts",
            "dataset_versions",
            "publications",
            "replays",
        }
        if set(raw) != expected:
            raise ValueError("V1 semantic export fields do not match schema.")
        if raw["schema"] != _EXPORT_SCHEMA or raw["schema_version"] != _EXPORT_VERSION:
            raise ValueError("Unsupported V1 semantic export schema/version.")
        source_version = raw["source_version"]
        if not isinstance(source_version, str) or not source_version.strip():
            raise ValueError("V1 semantic export source_version must be non-blank.")

        return cls(
            source_version=source_version,
            artifacts=_items(raw["artifacts"], LegacyArtifactSnapshot),
            dataset_versions=_items(
                raw["dataset_versions"],
                LegacyDatasetVersionSnapshot,
            ),
            publications=_items(
                raw["publications"],
                LegacyPublishedDatasetSnapshot,
            ),
            replays=_items(raw["replays"], LegacyReplaySnapshot),
        )


def _datetime_text(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("V1 semantic export requires timezone-aware datetimes.")
    return value.isoformat()


def _items(value: object, cls: type[Any]) -> tuple[Any, ...]:
    if not isinstance(value, list):
        raise ValueError("V1 semantic export collection must be a JSON array.")
    result: list[Any] = []
    field_names = set(cls.__dataclass_fields__)
    for item in value:
        if not isinstance(item, dict) or set(item) != field_names:
            raise ValueError(f"Invalid {cls.__name__} payload.")
        result.append(cls(**item))
    return tuple(result)
