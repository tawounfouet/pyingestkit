"""Structured acquisition requests and evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import (
    CorrelationContext,
    Diagnostic,
    FailureEvidence,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import (
    validate_aware_datetime,
    validate_metadata,
    validate_optional_text,
)
from pyingestkit.domain.sources import Source, SourceKind


class AcquisitionStatus(StrEnum):
    """Outcome of one ingestion-owned source acquisition."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN_OUTCOME = "unknown_outcome"
    REQUIRES_RECONCILIATION = "requires_reconciliation"

    @property
    def terminal(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    """One explicit acquisition request bound to an ingestion execution."""

    source: Source
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext

    def __post_init__(self) -> None:
        if not isinstance(self.source, Source):
            raise TypeError("AcquisitionRequest source must be a V2 Source.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError(
                "AcquisitionRequest ingestion_run_id must be an IngestionRunId."
            )
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError(
                "AcquisitionRequest correlation must be a CorrelationContext."
            )
        if (
            self.correlation.ingestion_run_id is not None
            and self.correlation.ingestion_run_id != str(self.ingestion_run_id)
        ):
            raise ValueError(
                "AcquisitionRequest correlation ingestion_run_id must match "
                "the native IngestionRunId."
            )


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    """Structured acquisition evidence plus bounded runtime-local content."""

    status: AcquisitionStatus
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    source_kind: SourceKind
    acquired_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    resource: ResourceReference | None = None
    content: bytes | None = None
    checksum_algorithm: str | None = None
    checksum: str | None = None
    size_bytes: int | None = None
    media_type: str | None = None
    source_metadata: tuple[tuple[str, str], ...] = ()
    provider_operation_id: str | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    failure: FailureEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, AcquisitionStatus):
            raise TypeError("AcquisitionResult status must be an AcquisitionStatus.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError(
                "AcquisitionResult ingestion_run_id must be an IngestionRunId."
            )
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError(
                "AcquisitionResult correlation must be a CorrelationContext."
            )
        if not isinstance(self.source_kind, SourceKind):
            raise TypeError("AcquisitionResult source_kind must be a SourceKind.")
        validate_aware_datetime(self.acquired_at, "AcquisitionResult acquired_at")

        if self.resource is not None and not isinstance(
            self.resource,
            ResourceReference,
        ):
            raise TypeError(
                "AcquisitionResult resource must be a ResourceReference."
            )
        if self.content is not None and not isinstance(self.content, bytes):
            raise TypeError("AcquisitionResult content must be bytes.")
        validate_optional_text(
            self.checksum_algorithm,
            "AcquisitionResult checksum_algorithm",
        )
        validate_optional_text(self.checksum, "AcquisitionResult checksum")
        if (self.checksum_algorithm is None) != (self.checksum is None):
            raise ValueError(
                "AcquisitionResult checksum_algorithm and checksum must be "
                "provided together."
            )

        if self.size_bytes is not None:
            if not isinstance(self.size_bytes, int):
                raise TypeError("AcquisitionResult size_bytes must be an int.")
            if self.size_bytes < 0:
                raise ValueError(
                    "AcquisitionResult size_bytes must be non-negative."
                )
        validate_optional_text(self.media_type, "AcquisitionResult media_type")
        validate_metadata(
            self.source_metadata,
            name="AcquisitionResult source_metadata",
        )
        validate_optional_text(
            self.provider_operation_id,
            "AcquisitionResult provider_operation_id",
        )

        if not isinstance(self.diagnostics, tuple):
            raise TypeError("AcquisitionResult diagnostics must be a tuple.")
        if any(not isinstance(item, Diagnostic) for item in self.diagnostics):
            raise TypeError(
                "AcquisitionResult diagnostics must contain Diagnostic values."
            )
        if self.failure is not None and not isinstance(
            self.failure,
            FailureEvidence,
        ):
            raise TypeError(
                "AcquisitionResult failure must be a FailureEvidence."
            )

        if self.status is AcquisitionStatus.SUCCEEDED:
            self._validate_success()
        elif self.failure is None:
            raise ValueError(
                "Non-successful AcquisitionResult requires FailureEvidence."
            )

    def _validate_success(self) -> None:
        if self.resource is None:
            raise ValueError(
                "Successful AcquisitionResult requires ResourceReference."
            )
        if self.content is None:
            raise ValueError(
                "Successful AcquisitionResult requires acquired content."
            )
        if self.checksum_algorithm is None or self.checksum is None:
            raise ValueError(
                "Successful AcquisitionResult requires checksum evidence."
            )
        if self.size_bytes is None:
            raise ValueError(
                "Successful AcquisitionResult requires size evidence."
            )
        if self.size_bytes != len(self.content):
            raise ValueError(
                "AcquisitionResult size_bytes must equal acquired content length."
            )
        if self.failure is not None:
            raise ValueError(
                "Successful AcquisitionResult cannot contain FailureEvidence."
            )
