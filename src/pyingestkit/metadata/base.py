from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from .models import (
    ArtifactRecord,
    EventRecord,
    PublicationRecord,
    RunRecord,
    StepRecord,
    ValidationRecord,
)

if TYPE_CHECKING:
    from pyingestkit.artifacts.raw import RawArtifact
    from pyingestkit.core.context import RunContext
    from pyingestkit.core.events import Event
    from pyingestkit.core.result import RunResult, StepResult


class MetadataStore(ABC):
    """Persistence contract for queryable runtime metadata.

    Implementations store lightweight operational state only. RAW payloads,
    reports and published datasets remain the responsibility of ArtifactStore.
    """

    @abstractmethod
    def initialize(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_run(self, context: RunContext) -> None:
        raise NotImplementedError

    @abstractmethod
    def finish_run(self, result: RunResult) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_step(self, run_id: str, position: int, result: StepResult) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        raise NotImplementedError

    @abstractmethod
    def record_event(self, event: Event) -> None:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def list_runs(
        self,
        *,
        job_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[RunRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def get_run(self, run_id_or_prefix: str) -> RunRecord:
        raise NotImplementedError

    @abstractmethod
    def list_steps(self, run_id: str) -> tuple[StepRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, run_id: str) -> tuple[EventRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def list_validations(self, run_id: str) -> tuple[ValidationRecord, ...]:
        raise NotImplementedError

    @abstractmethod
    def list_publications(self, run_id: str) -> tuple[PublicationRecord, ...]:
        raise NotImplementedError
