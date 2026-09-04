from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.core.context import RunContext
from pyingestkit.core.events import Event
from pyingestkit.core.result import RunResult, StepResult
from pyingestkit.logging.filters import redact_mapping

from .base import MetadataStore
from .capabilities import DiffMetadataCapability
from .models import (
    ArtifactRecord,
    DiffRecord,
    EventRecord,
    PublicationRecord,
    RunRecord,
    StepRecord,
    ValidationRecord,
)


def _event_level(event: Event) -> str:
    return "ERROR" if event.type.value.endswith("FAILED") else "INFO"


class MemoryMetadataStore(MetadataStore, DiffMetadataCapability):
    """Ephemeral MetadataStore useful for custom runtimes and unit tests."""

    def __init__(self) -> None:
        self.runs: dict[str, RunRecord] = {}
        self.steps: list[StepRecord] = []
        self.artifacts: list[ArtifactRecord] = []
        self.events: list[EventRecord] = []
        self.validations: list[ValidationRecord] = []
        self.publications: list[PublicationRecord] = []
        self.dataset_diffs: list[DiffRecord] = []

    def initialize(self) -> None:
        return None

    def start_run(self, context: RunContext) -> None:
        self.runs[str(context.run_id)] = RunRecord(
            run_id=str(context.run_id),
            job_id=context.job_id,
            job_version=context.job_version,
            status="RUNNING",
            started_at=context.started_at,
            completed_at=None,
            duration_seconds=None,
            fixture_mode=context.fixture_mode,
            parameters=redact_mapping(dict(context.parameters)),
            error=None,
            created_at=datetime.now(UTC),
        )

    def finish_run(self, result: RunResult) -> None:
        current = self.runs[result.run_id]
        self.runs[result.run_id] = replace(
            current,
            status=result.status.value,
            completed_at=result.completed_at,
            duration_seconds=result.duration_seconds,
            error=result.error,
        )

    def record_step(self, run_id: str, position: int, result: StepResult) -> None:
        self.steps = [
            row for row in self.steps if not (row.run_id == run_id and row.position == position)
        ]
        self.steps.append(
            StepRecord(
                id=len(self.steps) + 1,
                run_id=run_id,
                position=position,
                step_name=result.step_name,
                status=result.status.value,
                started_at=result.started_at,
                completed_at=result.completed_at,
                duration_seconds=result.duration_seconds,
                error=result.error,
                metrics=dict(result.metrics),
            )
        )

    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        if any(row.artifact_id == artifact.artifact_id for row in self.artifacts):
            return
        self.artifacts.append(
            ArtifactRecord(
                artifact_id=artifact.artifact_id,
                run_id=run_id,
                kind=kind,
                path=artifact.path,
                source_uri=artifact.source_uri,
                content_type=artifact.content_type,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
                created_at=artifact.retrieved_at,
                resolved_url=artifact.resolved_url,
                status_code=artifact.status_code,
                etag=artifact.etag,
                last_modified=artifact.last_modified,
            )
        )

    def record_event(self, event: Event) -> None:
        step = event.payload.get("step")
        self.events.append(
            EventRecord(
                id=len(self.events) + 1,
                run_id=event.run_id,
                job_id=event.job_id,
                step=str(step) if step else None,
                event_type=event.type.value,
                level=_event_level(event),
                message=event.type.value.replace("_", " ").title(),
                timestamp=event.timestamp,
                metadata=redact_mapping(dict(event.payload)),
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
        self.validations.append(
            ValidationRecord(
                id=len(self.validations) + 1,
                run_id=run_id,
                rule=rule,
                severity=severity,
                status=status,
                message=message,
                metadata=redact_mapping(dict(metadata or {})),
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
        self.publications.append(
            PublicationRecord(
                id=len(self.publications) + 1,
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
        rows = sorted(self.runs.values(), key=lambda row: row.started_at, reverse=True)
        if job_id:
            rows = [row for row in rows if row.job_id == job_id]
        if status:
            rows = [row for row in rows if row.status == status.upper()]
        return tuple(rows[: max(1, limit)])

    def get_run(self, run_id_or_prefix: str) -> RunRecord:
        if run_id_or_prefix in self.runs:
            return self.runs[run_id_or_prefix]
        matches = [row for key, row in self.runs.items() if key.startswith(run_id_or_prefix)]
        if not matches:
            raise KeyError(run_id_or_prefix)
        if len(matches) > 1:
            raise ValueError(f"Ambiguous run ID prefix: {run_id_or_prefix}")
        return matches[0]

    def list_steps(self, run_id: str) -> tuple[StepRecord, ...]:
        return tuple(
            sorted(
                (row for row in self.steps if row.run_id == run_id),
                key=lambda row: row.position,
            )
        )

    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        return tuple(row for row in self.artifacts if row.run_id == run_id)

    def list_events(self, run_id: str) -> tuple[EventRecord, ...]:
        return tuple(row for row in self.events if row.run_id == run_id)

    def list_validations(self, run_id: str) -> tuple[ValidationRecord, ...]:
        return tuple(row for row in self.validations if row.run_id == run_id)

    def list_publications(self, run_id: str) -> tuple[PublicationRecord, ...]:
        return tuple(row for row in self.publications if row.run_id == run_id)

    def record_dataset_diff(self, record: DiffRecord) -> None:
        next_id = len(self.dataset_diffs) + 1
        stored = replace(record, id=next_id) if record.id is None else record
        self.dataset_diffs.append(stored)

    def list_dataset_diffs(self, run_id: str) -> tuple[DiffRecord, ...]:
        return tuple(row for row in self.dataset_diffs if row.run_id == run_id)
