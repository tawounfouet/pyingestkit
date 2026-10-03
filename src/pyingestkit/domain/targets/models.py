"""Portable V2 target materialization contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import ClassVar

from pyingestkit.domain.datasets.references import DatasetVersionReference
from pyingestkit.domain.datasets.version import dataset_content_fingerprint
from pyingestkit.domain.decoding.models import DecodedRepresentation
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    FailureEvidence,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
    validate_optional_text,
)


class TargetLoadModeV2(StrEnum):
    """Portable target mutation semantics."""

    APPEND = "append"
    TRUNCATE_LOAD = "truncate_load"
    REPLACE = "replace"


class TargetLoadStatusV2(StrEnum):
    """Terminal target-load outcomes."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

    @property
    def terminal(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class TargetLoadRequestV2:
    """Materialize one exact immutable dataset version into one target."""

    target_id: str
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    dataset_version: DatasetVersionReference
    representation: DecodedRepresentation
    table: str
    schema: str | None = "public"
    mode: TargetLoadModeV2 = TargetLoadModeV2.APPEND
    expected_row_count: int | None = None
    columns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.target_id, "TargetLoadRequestV2 target_id")
        if "://" in self.target_id:
            raise ValueError("TargetLoadRequestV2 target_id must be logical, not a DSN.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("TargetLoadRequestV2 ingestion_run_id must be IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("TargetLoadRequestV2 correlation must be CorrelationContext.")
        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError("TargetLoadRequestV2 correlation run identity mismatch.")
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError(
                "TargetLoadRequestV2 dataset_version must be DatasetVersionReference."
            )
        if not isinstance(self.representation, DecodedRepresentation):
            raise TypeError(
                "TargetLoadRequestV2 representation must be DecodedRepresentation."
            )
        require_non_blank(self.table, "TargetLoadRequestV2 table")
        validate_optional_text(self.schema, "TargetLoadRequestV2 schema")
        if not isinstance(self.mode, TargetLoadModeV2):
            raise TypeError("TargetLoadRequestV2 mode must be TargetLoadModeV2.")
        if self.expected_row_count is not None:
            if not isinstance(self.expected_row_count, int):
                raise TypeError("TargetLoadRequestV2 expected_row_count must be int.")
            if self.expected_row_count < 0:
                raise ValueError("TargetLoadRequestV2 expected_row_count must be >= 0.")
            if self.expected_row_count != len(self.representation):
                raise ValueError(
                    "TargetLoadRequestV2 expected_row_count must equal representation length."
                )
        if not isinstance(self.columns, tuple):
            raise TypeError("TargetLoadRequestV2 columns must be a tuple.")
        if any(not isinstance(column, str) or not column.strip() for column in self.columns):
            raise ValueError("TargetLoadRequestV2 columns must contain non-blank strings.")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("TargetLoadRequestV2 columns must be unique.")

        actual_fingerprint = dataset_content_fingerprint(self.representation)
        if actual_fingerprint != self.dataset_version.version_id:
            raise ValueError(
                "TargetLoadRequestV2 representation does not match dataset version identity."
            )

        observed = self.observed_columns
        if self.columns:
            if set(self.columns) != set(observed):
                raise ValueError(
                    "TargetLoadRequestV2 columns must match decoded representation fields."
                )
        elif not observed:
            raise ValueError(
                "TargetLoadRequestV2 requires explicit columns for an empty representation."
            )

    @property
    def dataset_id(self) -> str:
        return self.dataset_version.dataset_id

    @property
    def resolved_columns(self) -> tuple[str, ...]:
        return self.columns or self.observed_columns

    @property
    def observed_columns(self) -> tuple[str, ...]:
        ordered: list[str] = []
        seen: set[str] = set()
        for record in self.representation.records:
            for name, _ in record.fields:
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
        return tuple(ordered)


@dataclass(frozen=True, slots=True)
class TargetLoadResultV2:
    """Portable evidence for one atomic target materialization attempt."""

    CONTRACT_ID: ClassVar[str] = "pykit.target_load_result"

    load_id: str
    target_id: str
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    dataset_version: DatasetVersionReference
    mode: TargetLoadModeV2
    status: TargetLoadStatusV2
    destination: str
    rows_input: int
    rows_loaded: int
    started_at: datetime
    completed_at: datetime
    diagnostics: tuple[Diagnostic, ...] = ()
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.load_id, "TargetLoadResultV2 load_id")
        require_non_blank(self.target_id, "TargetLoadResultV2 target_id")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("TargetLoadResultV2 ingestion_run_id must be IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("TargetLoadResultV2 correlation must be CorrelationContext.")
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError(
                "TargetLoadResultV2 dataset_version must be DatasetVersionReference."
            )
        if not isinstance(self.mode, TargetLoadModeV2):
            raise TypeError("TargetLoadResultV2 mode must be TargetLoadModeV2.")
        if not isinstance(self.status, TargetLoadStatusV2):
            raise TypeError("TargetLoadResultV2 status must be TargetLoadStatusV2.")
        require_non_blank(self.destination, "TargetLoadResultV2 destination")
        if not isinstance(self.rows_input, int) or self.rows_input < 0:
            raise ValueError("TargetLoadResultV2 rows_input must be int >= 0.")
        if not isinstance(self.rows_loaded, int) or self.rows_loaded < 0:
            raise ValueError("TargetLoadResultV2 rows_loaded must be int >= 0.")
        if self.rows_loaded > self.rows_input:
            raise ValueError("TargetLoadResultV2 rows_loaded cannot exceed rows_input.")
        validate_aware_datetime(self.started_at, "TargetLoadResultV2 started_at")
        validate_aware_datetime(self.completed_at, "TargetLoadResultV2 completed_at")
        if self.completed_at < self.started_at:
            raise ValueError("TargetLoadResultV2 completed_at cannot precede started_at.")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("TargetLoadResultV2 diagnostics must be a tuple.")
        if any(not isinstance(item, Diagnostic) for item in self.diagnostics):
            raise TypeError("TargetLoadResultV2 diagnostics must contain Diagnostic values.")
        if self.failure is not None and not isinstance(self.failure, FailureEvidence):
            raise TypeError("TargetLoadResultV2 failure must be FailureEvidence.")

        if self.status is TargetLoadStatusV2.SUCCEEDED:
            if self.failure is not None:
                raise ValueError("Successful TargetLoadResultV2 cannot contain failure.")
            if self.rows_loaded != self.rows_input:
                raise ValueError(
                    "Successful TargetLoadResultV2 must load every input row atomically."
                )
        elif self.failure is None:
            raise ValueError("Non-successful TargetLoadResultV2 requires FailureEvidence.")
