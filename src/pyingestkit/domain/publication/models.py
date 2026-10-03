"""Publication outcome and reconciliation contracts for PyIngestKit V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.runtime import (
    CorrelationContext,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
)


class PublicationStatusV2(StrEnum):
    """Terminal status of one governed publication attempt."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN_OUTCOME = "unknown_outcome"
    CONFLICT = "conflict"
    CANCELLED = "cancelled"


class PublicationReconciliationStatusV2(StrEnum):
    """Observed external truth after an uncertain publication."""

    CONFIRMED_COMMITTED = "confirmed_committed"
    CONFIRMED_NOT_COMMITTED = "confirmed_not_committed"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PublicationRequestV2:
    """Intent to make one immutable DatasetVersion the governed current version."""

    dataset_version: DatasetVersionReference
    ingestion_run_id: IngestionRunId
    correlation: CorrelationContext
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.dataset_version, DatasetVersionReference):
            raise TypeError("PublicationRequestV2 dataset_version must be DatasetVersionReference.")
        if not isinstance(self.ingestion_run_id, IngestionRunId):
            raise TypeError("PublicationRequestV2 ingestion_run_id must be IngestionRunId.")
        if not isinstance(self.correlation, CorrelationContext):
            raise TypeError("PublicationRequestV2 correlation must be CorrelationContext.")
        validate_aware_datetime(self.requested_at, "PublicationRequestV2 requested_at")
        if self.correlation.ingestion_run_id not in {
            None,
            str(self.ingestion_run_id),
        }:
            raise ValueError("PublicationRequestV2 correlation run identity mismatch.")


@dataclass(frozen=True, slots=True)
class PublicationResultV2:
    """Structured publication outcome that preserves provider uncertainty."""

    request: PublicationRequestV2
    status: PublicationStatusV2
    completed_at: datetime
    published_dataset: PublishedDataset | None = None
    failure: FailureEvidence | None = None
    provider_operation_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, PublicationRequestV2):
            raise TypeError("PublicationResultV2 request must be PublicationRequestV2.")
        if not isinstance(self.status, PublicationStatusV2):
            raise TypeError("PublicationResultV2 status must be PublicationStatusV2.")
        validate_aware_datetime(self.completed_at, "PublicationResultV2 completed_at")
        if self.completed_at < self.request.requested_at:
            raise ValueError("PublicationResultV2 completed_at cannot precede requested_at.")
        if self.provider_operation_reference is not None:
            require_non_blank(
                self.provider_operation_reference,
                "PublicationResultV2 provider_operation_reference",
            )

        if self.status is PublicationStatusV2.SUCCEEDED:
            if self.published_dataset is None:
                raise ValueError("Successful PublicationResultV2 requires PublishedDataset.")
            if self.failure is not None:
                raise ValueError("Successful PublicationResultV2 cannot contain failure.")
        else:
            if self.published_dataset is not None:
                raise ValueError(
                    "Non-successful PublicationResultV2 cannot expose PublishedDataset."
                )
            if self.failure is None:
                raise ValueError("Non-successful PublicationResultV2 requires FailureEvidence.")

        if self.published_dataset is not None:
            if self.published_dataset.version.identity != self.request.dataset_version.identity:
                raise ValueError("PublicationResultV2 published version identity mismatch.")

        if self.failure is not None:
            if self.failure.ingestion_run_id != self.request.ingestion_run_id:
                raise ValueError("PublicationResultV2 failure run identity mismatch.")
            if self.failure.correlation_id != self.request.correlation.correlation_id:
                raise ValueError("PublicationResultV2 failure correlation identity mismatch.")

        if self.status is PublicationStatusV2.UNKNOWN_OUTCOME:
            if self.failure is None:
                raise AssertionError("UNKNOWN_OUTCOME requires FailureEvidence.")
            if self.failure.category is not FailureCategory.UNKNOWN_OUTCOME:
                raise ValueError(
                    "UNKNOWN_OUTCOME PublicationResultV2 requires UNKNOWN_OUTCOME failure."
                )
            if self.failure.uncertainty is not OutcomeUncertainty.REQUIRES_RECONCILIATION:
                raise ValueError("UNKNOWN_OUTCOME publication must require reconciliation.")

    @property
    def succeeded(self) -> bool:
        return self.status is PublicationStatusV2.SUCCEEDED

    @property
    def reconciliation_required(self) -> bool:
        return self.status is PublicationStatusV2.UNKNOWN_OUTCOME


@dataclass(frozen=True, slots=True)
class PublicationReconciliationResultV2:
    """External-truth inspection for one prior publication request."""

    request: PublicationRequestV2
    status: PublicationReconciliationStatusV2
    reconciled_at: datetime
    published_dataset: PublishedDataset | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, PublicationRequestV2):
            raise TypeError(
                "PublicationReconciliationResultV2 request must be PublicationRequestV2."
            )
        if not isinstance(self.status, PublicationReconciliationStatusV2):
            raise TypeError(
                "PublicationReconciliationResultV2 status must be "
                "PublicationReconciliationStatusV2."
            )
        validate_aware_datetime(
            self.reconciled_at,
            "PublicationReconciliationResultV2 reconciled_at",
        )
        if self.published_dataset is not None and not isinstance(
            self.published_dataset,
            PublishedDataset,
        ):
            raise TypeError(
                "PublicationReconciliationResultV2 published_dataset must be PublishedDataset."
            )
        if (
            self.status is PublicationReconciliationStatusV2.CONFIRMED_COMMITTED
            and self.published_dataset is None
        ):
            raise ValueError("Confirmed publication requires PublishedDataset evidence.")
        if (
            self.status is PublicationReconciliationStatusV2.CONFIRMED_NOT_COMMITTED
            and self.published_dataset is not None
        ):
            raise ValueError("Not-committed reconciliation cannot expose PublishedDataset.")
