"""Immutable V2 ingestion run/result lifecycle contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.runtime.context import CorrelationContext
from pyingestkit.domain.runtime.diagnostics import Diagnostic
from pyingestkit.domain.runtime.failure import FailureEvidence
from pyingestkit.domain.runtime.status import IngestionStatus
from pyingestkit.domain.shared.identifiers import IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
)


@dataclass(frozen=True, slots=True)
class IngestionRun:
    """Immutable lifecycle snapshot for one semantic ingestion execution."""

    ingestion_run_id: IngestionRunId
    ingestion_definition_name: str
    definition_fingerprint: str
    correlation: CorrelationContext
    status: IngestionStatus
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("IngestionRun ingestion_run_id must be IngestionRunId.")
        require_non_blank(
            self.ingestion_definition_name,
            "IngestionRun ingestion_definition_name",
        )
        require_non_blank(self.definition_fingerprint, "IngestionRun definition_fingerprint")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("IngestionRun correlation must be CorrelationContext.")
        if not isinstance(self.status, IngestionStatus):
            raise TypeError("IngestionRun status must be IngestionStatus.")
        if not isinstance(self.created_at, datetime):
            raise TypeError("IngestionRun created_at must be datetime.")
        validate_aware_datetime(self.created_at, "IngestionRun created_at")
        validate_aware_datetime(self.started_at, "IngestionRun started_at")
        validate_aware_datetime(self.ended_at, "IngestionRun ended_at")

        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError(
                "IngestionRun correlation ingestion_run_id must match native run identity."
            )
        if self.status is IngestionStatus.CREATED:
            if self.started_at is not None or self.ended_at is not None:
                raise ValueError("CREATED IngestionRun cannot have start/end timestamps.")
        elif self.status is IngestionStatus.RUNNING:
            if self.started_at is None or self.ended_at is not None:
                raise ValueError("RUNNING IngestionRun requires started_at and no ended_at.")
        elif self.status.terminal and self.ended_at is None:
            raise ValueError("Terminal IngestionRun requires ended_at.")

        if self.started_at is not None and self.started_at < self.created_at:
            raise ValueError("IngestionRun started_at cannot precede created_at.")
        if self.ended_at is not None:
            lower_bound = self.started_at or self.created_at
            if self.ended_at < lower_bound:
                raise ValueError("IngestionRun ended_at cannot precede lifecycle start.")

    @property
    def terminal(self) -> bool:
        return self.status.terminal


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """Terminal portable result for one semantic ingestion execution."""

    run: IngestionRun
    raw_artifact: ArtifactReference | None = None
    dataset_version: DatasetVersionReference | None = None
    published_dataset: PublishedDataset | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.run, IngestionRun):
            raise TypeError("IngestionResult run must be IngestionRun.")
        if not self.run.terminal:
            raise ValueError("IngestionResult requires a terminal IngestionRun.")
        if self.raw_artifact is not None and not isinstance(\n            self.raw_artifact,\n            ArtifactReference,\n        ):\n            raise TypeError("IngestionResult raw_artifact must be ArtifactReference.")\n        if self.dataset_version is not None and not isinstance(\n            self.dataset_version,
            DatasetVersionReference,
        ):
            raise TypeError("IngestionResult dataset_version must be DatasetVersionReference.")
        if self.published_dataset is not None and not isinstance(
            self.published_dataset,
            PublishedDataset,
        ):
            raise TypeError("IngestionResult published_dataset must be PublishedDataset.")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("IngestionResult diagnostics must be a tuple.")
        if any(not isinstance(item, Diagnostic) for item in self.diagnostics):
            raise TypeError("IngestionResult diagnostics must contain Diagnostic values.")
        if self.failure is not None and not isinstance(self.failure, FailureEvidence):
            raise TypeError("IngestionResult failure must be FailureEvidence.")

        if self.run.status is IngestionStatus.SUCCEEDED and self.failure is not None:
            raise ValueError("Successful IngestionResult cannot contain FailureEvidence.")
        if self.run.status is not IngestionStatus.SUCCEEDED and self.failure is None:
            raise ValueError("Non-successful IngestionResult requires FailureEvidence.")

        if self.failure is not None:
            if self.failure.ingestion_run_id != self.run.ingestion_run_id:
                raise ValueError("IngestionResult failure run identity mismatch.")
            if self.failure.correlation_id != self.run.correlation.correlation_id:
                raise ValueError("IngestionResult failure correlation identity mismatch.")

        for diagnostic in self.diagnostics:
            if (
                diagnostic.ingestion_run_id is not None
                and diagnostic.ingestion_run_id != self.run.ingestion_run_id
            ):
                raise ValueError("IngestionResult diagnostic run identity mismatch.")
            if (
                diagnostic.correlation_id is not None
                and diagnostic.correlation_id != self.run.correlation.correlation_id
            ):
                raise ValueError("IngestionResult diagnostic correlation identity mismatch.")

        if self.published_dataset is not None:
            if self.dataset_version is None:
                raise ValueError(
                    "IngestionResult published_dataset requires dataset_version evidence."
                )
            if self.published_dataset.version.identity != self.dataset_version.identity:
                raise ValueError("IngestionResult published dataset/version identity mismatch.")

    @property
    def status(self) -> IngestionStatus:
        return self.run.status

    @property
    def ingestion_run_id(self) -> IngestionRunId:
        return self.run.ingestion_run_id

    @property
    def succeeded(self) -> bool:
        return self.run.status is IngestionStatus.SUCCEEDED
