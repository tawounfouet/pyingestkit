"""Portable V2 dataset materialization contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pyingestkit.domain.datasets.version import DatasetVersion
from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    FailureEvidence,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import validate_aware_datetime


class MaterializationMode(StrEnum):
    """Provider-neutral destination mutation semantics."""

    APPEND = "append"
    TRUNCATE_LOAD = "truncate_load"
    REPLACE = "replace"


class MaterializationStatus(StrEnum):
    """Terminal outcome of one materialization attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def terminal(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class MaterializationRequest:
    """Request to materialize one exact immutable DatasetVersion."""

    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    dataset_version: DatasetVersion
    destination: ResourceReference
    mode: MaterializationMode = MaterializationMode.APPEND

    def __post_init__(self) -> None:
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("MaterializationRequest ingestion_run_id must be IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("MaterializationRequest correlation must be CorrelationContext.")
        if not isinstance(self.dataset_version, DatasetVersion):
            raise TypeError("MaterializationRequest dataset_version must be DatasetVersion.")
        if not isinstance(self.destination, ResourceReference):
            raise TypeError("MaterializationRequest destination must be ResourceReference.")
        if not isinstance(self.mode, MaterializationMode):
            raise TypeError("MaterializationRequest mode must be MaterializationMode.")
        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError(
                "MaterializationRequest correlation ingestion_run_id must match native run id."
            )
        if self.dataset_version.ingestion_run_id != self.ingestion_run_id:
            raise ValueError(
                "MaterializationRequest dataset version must belong to the materializing run."
            )


@dataclass(frozen=True, slots=True)
class MaterializationResult:
    """Portable materialization evidence with no provider credentials."""

    status: MaterializationStatus
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    dataset_version: DatasetVersionReference
    destination: ResourceReference
    mode: MaterializationMode
    rows_input: int
    rows_loaded: int
    started_at: datetime
    completed_at: datetime
    rows_cleared: int = 0
    diagnostics: tuple[Diagnostic, ...] = ()
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, MaterializationStatus):
            raise TypeError("MaterializationResult status must be MaterializationStatus.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("MaterializationResult ingestion_run_id must be IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("MaterializationResult correlation must be CorrelationContext.")
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError(
                "MaterializationResult dataset_version must be DatasetVersionReference."
            )
        if not isinstance(self.destination, ResourceReference):
            raise TypeError("MaterializationResult destination must be ResourceReference.")
        if not isinstance(self.mode, MaterializationMode):
            raise TypeError("MaterializationResult mode must be MaterializationMode.")
        for label, value in (
            ("rows_input", self.rows_input),
            ("rows_loaded", self.rows_loaded),
            ("rows_cleared", self.rows_cleared),
        ):
            if not isinstance(value, int):
                raise TypeError(f"MaterializationResult {label} must be int.")
            if value < 0:
                raise ValueError(f"MaterializationResult {label} must be non-negative.")
        validate_aware_datetime(self.started_at, "MaterializationResult started_at")
        validate_aware_datetime(self.completed_at, "MaterializationResult completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("MaterializationResult completed_at must not precede started_at.")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("MaterializationResult diagnostics must be a tuple.")
        if any(not isinstance(item, Diagnostic) for item in self.diagnostics):
            raise TypeError("MaterializationResult diagnostics must contain Diagnostic values.")
        if self.failure is not None and not isinstance(self.failure, FailureEvidence):
            raise TypeError("MaterializationResult failure must be FailureEvidence.")

        if self.status is MaterializationStatus.SUCCEEDED:
            if self.failure is not None:
                raise ValueError("Successful MaterializationResult cannot contain failure.")
            if self.rows_loaded != self.rows_input:
                raise ValueError(
                    "Successful MaterializationResult must load exactly rows_input rows."
                )
        elif self.failure is None:
            raise ValueError("Failed MaterializationResult requires FailureEvidence.")

    @property
    def succeeded(self) -> bool:
        return self.status is MaterializationStatus.SUCCEEDED

    @property
    def portable(self) -> bool:
        return True
