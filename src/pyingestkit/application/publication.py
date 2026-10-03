"""Explicit V2 publication and reconciliation service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from pyingestkit.domain.publication import (
    PublicationReconciliationResultV2,
    PublicationReconciliationStatusV2,
    PublicationRequestV2,
    PublicationResultV2,
    PublicationStatusV2,
)
from pyingestkit.domain.runtime import (
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.ports.dataset_versions import DatasetPublisher


class PublicationOutcomeUnknownError(RuntimeError):
    """Signal that the provider may have committed but acknowledgement was lost."""

    def __init__(
        self,
        message: str,
        *,
        provider_operation_reference: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider_operation_reference = provider_operation_reference


class PublicationServiceV2:
    """Publish immutable versions and reconcile uncertain pointer updates."""

    def __init__(
        self,
        *,
        publisher: DatasetPublisher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(publisher, DatasetPublisher):
            raise TypeError("PublicationServiceV2 publisher must satisfy DatasetPublisher.")
        self._publisher = publisher
        self._clock = clock or (lambda: datetime.now(UTC))

    def publish(self, request: PublicationRequestV2) -> PublicationResultV2:
        if not isinstance(request, PublicationRequestV2):
            raise TypeError("PublicationServiceV2.publish requires PublicationRequestV2.")

        current = self._publisher.get_published(request.dataset_version.dataset_id)
        if current is not None and current.version.identity == request.dataset_version.identity:
            return PublicationResultV2(
                request=request,
                status=PublicationStatusV2.SUCCEEDED,
                completed_at=self._now(),
                published_dataset=current,
            )

        try:
            published = self._publisher.publish(
                request.dataset_version,
                ingestion_run_id=request.ingestion_run_id,
                published_at=self._now(),
            )
        except PublicationOutcomeUnknownError as exc:
            failure = FailureEvidence(
                error_code="publication.unknown_outcome",
                category=FailureCategory.UNKNOWN_OUTCOME,
                retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
                uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
                ingestion_run_id=request.ingestion_run_id,
                correlation_id=request.correlation.correlation_id,
                source_component="publication",
                provider_code="acknowledgement_lost",
                message_summary="Publication outcome requires reconciliation.",
            )
            return PublicationResultV2(
                request=request,
                status=PublicationStatusV2.UNKNOWN_OUTCOME,
                completed_at=self._now(),
                failure=failure,
                provider_operation_reference=exc.provider_operation_reference,
            )

        return PublicationResultV2(
            request=request,
            status=PublicationStatusV2.SUCCEEDED,
            completed_at=self._now(),
            published_dataset=published,
        )

    def reconcile(
        self,
        request: PublicationRequestV2,
    ) -> PublicationReconciliationResultV2:
        """Inspect current provider truth without retrying the publication."""

        if not isinstance(request, PublicationRequestV2):
            raise TypeError("PublicationServiceV2.reconcile requires PublicationRequestV2.")
        current = self._publisher.get_published(request.dataset_version.dataset_id)

        if current is None:
            status = PublicationReconciliationStatusV2.CONFIRMED_NOT_COMMITTED
        elif current.version.identity == request.dataset_version.identity:
            status = PublicationReconciliationStatusV2.CONFIRMED_COMMITTED
        else:
            status = PublicationReconciliationStatusV2.CONFLICT

        return PublicationReconciliationResultV2(
            request=request,
            status=status,
            reconciled_at=self._now(),
            published_dataset=current,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError("PublicationServiceV2 clock must return aware datetime.")
        return value
