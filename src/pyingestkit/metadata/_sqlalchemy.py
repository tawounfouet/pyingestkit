from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Engine, RowMapping

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event
from pyingestkit.core.result import RunResult, StepResult
from pyingestkit.logging.filters import redact_mapping

from ._schema import (
    artifact_http_provenance,
    artifacts,
    dataset_diffs,
    dataset_version_runs,
    dataset_versions,
    events,
    metadata,
    publications,
    published_datasets,
    runs,
    steps,
    validations,
)
from .base import MetadataStore
from .capabilities import DiffMetadataCapability, VersionMetadataCapability
from .models import (
    ArtifactRecord,
    DatasetVersionRecord,
    DatasetVersionRunRecord,
    DiffRecord,
    EventRecord,
    PublicationRecord,
    PublishedDatasetRecord,
    RunRecord,
    StepRecord,
    ValidationRecord,
)


def _event_level(event: Event) -> str:
    return "ERROR" if event.type.value.endswith("FAILED") else "INFO"


def _json_safe(value: object) -> Any:
    """Return a JSON-compatible value while preserving redaction semantics."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return {}


def _required_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Expected datetime-compatible value, got {type(value).__name__}")


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return _required_datetime(value)


class _SQLAlchemyMetadataStore(MetadataStore, DiffMetadataCapability, VersionMetadataCapability):
    """Shared SQLAlchemy Core implementation behind concrete metadata adapters."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.initialize()

    def initialize(self) -> None:
        # New provenance capabilities use additive tables so existing Alpha 1
        # SQLite/PostgreSQL metadata remains readable without in-place ALTERs.
        metadata.create_all(self.engine)

    def start_run(self, context: RunContext) -> None:
        parameters = _json_safe(redact_mapping(dict(context.parameters)))
        with self.engine.begin() as connection:
            connection.execute(
                insert(runs).values(
                    run_id=str(context.run_id),
                    job_id=context.job_id,
                    job_version=context.job_version,
                    status="RUNNING",
                    started_at=context.started_at,
                    completed_at=None,
                    duration_seconds=None,
                    fixture_mode=context.fixture_mode,
                    parameters_json=parameters,
                    error=None,
                    created_at=datetime.now(UTC),
                )
            )

    def finish_run(self, result: RunResult) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(runs)
                .where(runs.c.run_id == result.run_id)
                .values(
                    status=result.status.value,
                    completed_at=result.completed_at,
                    duration_seconds=result.duration_seconds,
                    error=result.error,
                )
            )

    def record_step(self, run_id: str, position: int, result: StepResult) -> None:
        values = {
            "run_id": run_id,
            "position": position,
            "step_name": result.step_name,
            "status": result.status.value,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "duration_seconds": result.duration_seconds,
            "error": result.error,
            "metrics_json": _json_safe(result.metrics),
        }
        with self.engine.begin() as connection:
            existing_id = connection.execute(
                select(steps.c.id).where(
                    steps.c.run_id == run_id,
                    steps.c.position == position,
                )
            ).scalar_one_or_none()
            if existing_id is None:
                connection.execute(insert(steps).values(**values))
            else:
                connection.execute(update(steps).where(steps.c.id == existing_id).values(**values))

    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(artifacts.c.artifact_id).where(
                    artifacts.c.artifact_id == artifact.artifact_id
                )
            ).scalar_one_or_none()
            if exists is not None:
                return
            connection.execute(
                insert(artifacts).values(
                    artifact_id=artifact.artifact_id,
                    run_id=run_id,
                    kind=kind,
                    path=artifact.path,
                    source_uri=artifact.source_uri,
                    content_type=artifact.content_type,
                    size_bytes=artifact.size_bytes,
                    sha256=artifact.sha256,
                    created_at=artifact.retrieved_at,
                )
            )
            if artifact.status_code is not None:
                connection.execute(
                    insert(artifact_http_provenance).values(
                        artifact_id=artifact.artifact_id,
                        resolved_url=artifact.resolved_url,
                        status_code=artifact.status_code,
                        etag=artifact.etag,
                        last_modified=artifact.last_modified,
                    )
                )

    def record_event(self, event: Event) -> None:
        step = event.payload.get("step")
        with self.engine.begin() as connection:
            connection.execute(
                insert(events).values(
                    run_id=event.run_id,
                    job_id=event.job_id,
                    step=str(step) if step else None,
                    event_type=event.type.value,
                    level=_event_level(event),
                    message=event.type.value.replace("_", " ").title(),
                    timestamp=event.timestamp,
                    metadata_json=_json_safe(redact_mapping(dict(event.payload))),
                )
            )

    def record_validation(
        self,
        run_id: str,
        *,
        rule: str,
        severity: str,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(validations).values(
                    run_id=run_id,
                    rule=rule,
                    severity=severity,
                    status=status,
                    message=message,
                    metadata_json=_json_safe(redact_mapping(dict(metadata or {}))),
                )
            )

    def record_publication(
        self,
        run_id: str,
        *,
        dataset_id: str,
        status: str,
        candidate_path: str | None = None,
        published_path: str | None = None,
        published_at: datetime | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(publications).values(
                    run_id=run_id,
                    dataset_id=dataset_id,
                    status=status,
                    candidate_path=candidate_path,
                    published_path=published_path,
                    published_at=published_at,
                )
            )

    def list_runs(
        self,
        *,
        job_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[RunRecord, ...]:
        statement = select(runs)
        if job_id is not None:
            statement = statement.where(runs.c.job_id == job_id)
        if status is not None:
            statement = statement.where(runs.c.status == status.upper())
        statement = statement.order_by(runs.c.started_at.desc()).limit(max(1, limit))
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return tuple(self._run_record(row) for row in rows)

    def get_run(self, run_id_or_prefix: str) -> RunRecord:
        with self.engine.connect() as connection:
            exact = (
                connection.execute(select(runs).where(runs.c.run_id == run_id_or_prefix))
                .mappings()
                .one_or_none()
            )
            if exact is not None:
                return self._run_record(exact)
            matches = (
                connection.execute(
                    select(runs)
                    .where(runs.c.run_id.like(f"{run_id_or_prefix}%"))
                    .order_by(runs.c.started_at.desc())
                    .limit(2)
                )
                .mappings()
                .all()
            )
        if not matches:
            raise KeyError(run_id_or_prefix)
        if len(matches) > 1:
            raise ValueError(f"Ambiguous run ID prefix: {run_id_or_prefix}")
        return self._run_record(matches[0])

    def list_steps(self, run_id: str) -> tuple[StepRecord, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(steps).where(steps.c.run_id == run_id).order_by(steps.c.position)
                )
                .mappings()
                .all()
            )
        return tuple(
            StepRecord(
                id=cast(int | None, row["id"]),
                run_id=cast(str, row["run_id"]),
                position=cast(int, row["position"]),
                step_name=cast(str, row["step_name"]),
                status=cast(str, row["status"]),
                started_at=_required_datetime(row["started_at"]),
                completed_at=_required_datetime(row["completed_at"]),
                duration_seconds=cast(float, row["duration_seconds"]),
                error=cast(str | None, row["error"]),
                metrics=_mapping(row["metrics_json"]),
            )
            for row in rows
        )

    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        statement = (
            select(
                artifacts,
                artifact_http_provenance.c.resolved_url,
                artifact_http_provenance.c.status_code,
                artifact_http_provenance.c.etag,
                artifact_http_provenance.c.last_modified,
            )
            .outerjoin(
                artifact_http_provenance,
                artifact_http_provenance.c.artifact_id == artifacts.c.artifact_id,
            )
            .where(artifacts.c.run_id == run_id)
            .order_by(artifacts.c.created_at)
        )
        with self.engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return tuple(
            ArtifactRecord(
                artifact_id=cast(str, row["artifact_id"]),
                run_id=cast(str, row["run_id"]),
                kind=cast(str, row["kind"]),
                path=cast(str, row["path"]),
                source_uri=cast(str, row["source_uri"]),
                content_type=cast(str | None, row["content_type"]),
                size_bytes=cast(int, row["size_bytes"]),
                sha256=cast(str, row["sha256"]),
                created_at=_required_datetime(row["created_at"]),
                resolved_url=cast(str | None, row["resolved_url"]),
                status_code=cast(int | None, row["status_code"]),
                etag=cast(str | None, row["etag"]),
                last_modified=cast(str | None, row["last_modified"]),
            )
            for row in rows
        )

    def list_events(self, run_id: str) -> tuple[EventRecord, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(events).where(events.c.run_id == run_id).order_by(events.c.id)
                )
                .mappings()
                .all()
            )
        return tuple(
            EventRecord(
                id=cast(int | None, row["id"]),
                run_id=cast(str, row["run_id"]),
                job_id=cast(str, row["job_id"]),
                step=cast(str | None, row["step"]),
                event_type=cast(str, row["event_type"]),
                level=cast(str, row["level"]),
                message=cast(str, row["message"]),
                timestamp=_required_datetime(row["timestamp"]),
                metadata=_mapping(row["metadata_json"]),
            )
            for row in rows
        )

    def list_validations(self, run_id: str) -> tuple[ValidationRecord, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(validations)
                    .where(validations.c.run_id == run_id)
                    .order_by(validations.c.id)
                )
                .mappings()
                .all()
            )
        return tuple(
            ValidationRecord(
                id=cast(int | None, row["id"]),
                run_id=cast(str, row["run_id"]),
                rule=cast(str, row["rule"]),
                severity=cast(str, row["severity"]),
                status=cast(str, row["status"]),
                message=cast(str, row["message"]),
                metadata=_mapping(row["metadata_json"]),
            )
            for row in rows
        )

    def list_publications(self, run_id: str) -> tuple[PublicationRecord, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(publications)
                    .where(publications.c.run_id == run_id)
                    .order_by(publications.c.id)
                )
                .mappings()
                .all()
            )
        return tuple(
            PublicationRecord(
                id=cast(int | None, row["id"]),
                run_id=cast(str, row["run_id"]),
                dataset_id=cast(str, row["dataset_id"]),
                status=cast(str, row["status"]),
                candidate_path=cast(str | None, row["candidate_path"]),
                published_path=cast(str | None, row["published_path"]),
                published_at=_optional_datetime(row["published_at"]),
            )
            for row in rows
        )

    def record_dataset_diff(self, record: DiffRecord) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(dataset_diffs).values(
                    run_id=record.run_id,
                    step_name=record.step_name,
                    dataset_id=record.dataset_id,
                    previous_version_id=record.previous_version_id,
                    candidate_fingerprint=record.candidate_fingerprint,
                    added_count=record.added_count,
                    removed_count=record.removed_count,
                    changed_count=record.changed_count,
                    unchanged_count=record.unchanged_count,
                    entries_truncated=record.entries_truncated,
                    report_path=record.report_path,
                    created_at=record.created_at,
                )
            )

    def list_dataset_diffs(self, run_id: str) -> tuple[DiffRecord, ...]:
        with self.engine.connect() as connection:
            rows = (
                connection.execute(
                    select(dataset_diffs)
                    .where(dataset_diffs.c.run_id == run_id)
                    .order_by(dataset_diffs.c.id)
                )
                .mappings()
                .all()
            )
        return tuple(
            DiffRecord(
                id=cast(int | None, row["id"]),
                run_id=cast(str, row["run_id"]),
                step_name=cast(str, row["step_name"]),
                dataset_id=cast(str, row["dataset_id"]),
                previous_version_id=cast(str, row["previous_version_id"]),
                candidate_fingerprint=cast(str, row["candidate_fingerprint"]),
                added_count=cast(int, row["added_count"]),
                removed_count=cast(int, row["removed_count"]),
                changed_count=cast(int, row["changed_count"]),
                unchanged_count=cast(int, row["unchanged_count"]),
                entries_truncated=bool(row["entries_truncated"]),
                report_path=cast(str, row["report_path"]),
                created_at=_required_datetime(row["created_at"]),
            )
            for row in rows
        )

    @staticmethod
    def _run_record(row: RowMapping) -> RunRecord:
        return RunRecord(
            run_id=cast(str, row["run_id"]),
            job_id=cast(str, row["job_id"]),
            job_version=cast(str, row["job_version"]),
            status=cast(str, row["status"]),
            started_at=_required_datetime(row["started_at"]),
            completed_at=_optional_datetime(row["completed_at"]),
            duration_seconds=cast(float | None, row["duration_seconds"]),
            fixture_mode=bool(row["fixture_mode"]),
            parameters=_mapping(row["parameters_json"]),
            error=cast(str | None, row["error"]),
            created_at=_required_datetime(row["created_at"]),
        )


    def record_dataset_version(self, record: DatasetVersionRecord) -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(dataset_versions.c.version_id).where(
                    dataset_versions.c.dataset_id == record.dataset_id,
                    dataset_versions.c.version_id == record.version_id,
                )
            ).first()
            if exists is None:
                connection.execute(
                    insert(dataset_versions).values(
                        dataset_id=record.dataset_id,
                        version_id=record.version_id,
                        fingerprint=record.fingerprint,
                        snapshot_uri=record.snapshot_uri,
                        created_from_run_id=record.created_from_run_id,
                        job_id=record.job_id,
                        job_version=record.job_version,
                        source_artifact_id=record.source_artifact_id,
                        source_raw_sha256=record.source_raw_sha256,
                        created_at=record.created_at,
                    )
                )

    def record_dataset_version_run(self, record: DatasetVersionRunRecord) -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(dataset_version_runs.c.run_id).where(
                    dataset_version_runs.c.dataset_id == record.dataset_id,
                    dataset_version_runs.c.version_id == record.version_id,
                    dataset_version_runs.c.run_id == record.run_id,
                )
            ).first()
            if exists is None:
                connection.execute(
                    insert(dataset_version_runs).values(
                        dataset_id=record.dataset_id,
                        version_id=record.version_id,
                        run_id=record.run_id,
                        created_at=record.created_at,
                    )
                )

    def list_dataset_versions(self, dataset_id: str) -> tuple[DatasetVersionRecord, ...]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(dataset_versions)
                .where(dataset_versions.c.dataset_id == dataset_id)
                .order_by(dataset_versions.c.created_at.desc(), dataset_versions.c.version_id.desc())
            ).mappings().all()
        return tuple(
            DatasetVersionRecord(
                dataset_id=cast(str, row["dataset_id"]),
                version_id=cast(str, row["version_id"]),
                fingerprint=cast(str, row["fingerprint"]),
                snapshot_uri=cast(str, row["snapshot_uri"]),
                created_from_run_id=cast(str, row["created_from_run_id"]),
                job_id=cast(str, row["job_id"]),
                job_version=cast(str, row["job_version"]),
                source_artifact_id=cast(str | None, row["source_artifact_id"]),
                source_raw_sha256=cast(str | None, row["source_raw_sha256"]),
                created_at=_required_datetime(row["created_at"]),
            )
            for row in rows
        )

    def record_published_dataset(self, record: PublishedDatasetRecord) -> None:
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(published_datasets.c.dataset_id).where(
                    published_datasets.c.dataset_id == record.dataset_id
                )
            ).first()
            values = dict(
                version_id=record.version_id,
                published_from_run_id=record.published_from_run_id,
                published_at=record.published_at,
            )
            if exists is None:
                connection.execute(
                    insert(published_datasets).values(dataset_id=record.dataset_id, **values)
                )
            else:
                connection.execute(
                    published_datasets.update()
                    .where(published_datasets.c.dataset_id == record.dataset_id)
                    .values(**values)
                )

    def get_published_dataset(self, dataset_id: str) -> PublishedDatasetRecord | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(published_datasets).where(published_datasets.c.dataset_id == dataset_id)
            ).mappings().one_or_none()
        if row is None:
            return None
        return PublishedDatasetRecord(
            dataset_id=cast(str, row["dataset_id"]),
            version_id=cast(str, row["version_id"]),
            published_from_run_id=cast(str, row["published_from_run_id"]),
            published_at=_required_datetime(row["published_at"]),
        )
