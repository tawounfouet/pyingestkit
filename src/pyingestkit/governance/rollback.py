"""Governed rollback service for PyIngestKit 2.1 LOT-28."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, cast, runtime_checkable

from pyingestkit.domain.governance import (
    ConditionalPublicationOutcome,
    ConditionalPublicationStatus,
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
)
from pyingestkit.domain.runtime import (
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.ports.dataset_versions import DatasetVersionStore
from pyingestkit.ports.governance import ConditionalDatasetPublisher, PublicationLedger


@runtime_checkable
class _LifecycleEventReader(Protocol):
    def list_events(
        self,
        operation_id: PublicationOperationId | None = None,
        *,
        dataset_id: str | None = None,
    ) -> tuple[PublicationLifecycleEvent, ...]: ...


class GovernedRollbackService:
    """Rollback by conditionally publishing one existing immutable DatasetVersion."""

    def __init__(
        self,
        *,
        store: DatasetVersionStore,
        publisher: ConditionalDatasetPublisher,
        ledger: PublicationLedger,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(store, DatasetVersionStore):
            raise TypeError("GovernedRollbackService store must satisfy DatasetVersionStore.")
        if not isinstance(publisher, ConditionalDatasetPublisher):
            raise TypeError(
                "GovernedRollbackService publisher must satisfy ConditionalDatasetPublisher."
            )
        if not isinstance(ledger, PublicationLedger):
            raise TypeError("GovernedRollbackService ledger must satisfy PublicationLedger.")
        if not isinstance(ledger, _LifecycleEventReader):
            raise TypeError(
                "GovernedRollbackService ledger must expose append-only lifecycle event history."
            )
        self._store = store
        self._publisher = publisher
        self._ledger = ledger
        self._clock = clock or (lambda: datetime.now(UTC))

    def rollback(self, intent: PublicationIntent) -> ConditionalPublicationOutcome:
        """Publish an already-stored historical version through the frozen CAS contract."""
        if not isinstance(intent, PublicationIntent):
            raise TypeError("GovernedRollbackService.rollback requires PublicationIntent.")

        invalid = self._validate_target(intent)
        if invalid is not None:
            return invalid

        self._ensure_rollback_registered(intent)
        return self._publisher.compare_and_publish(intent)

    def reconcile(self, intent: PublicationIntent) -> ConditionalPublicationOutcome:
        """Reconcile an admitted rollback without issuing another publication write."""
        if not isinstance(intent, PublicationIntent):
            raise TypeError("GovernedRollbackService.reconcile requires PublicationIntent.")
        existing = self._ledger.get_operation(intent.operation_id)
        if existing is None:
            raise KeyError(str(intent.operation_id))
        existing.assert_same_intent_as(intent)
        if not operation_is_rollback(self._ledger, intent.operation_id):
            raise ValueError("Publication operation is not a governed rollback.")

        reconcile = getattr(self._publisher, "reconcile", None)
        if not callable(reconcile):
            raise TypeError("Conditional publisher does not expose reconciliation capability.")
        return cast(ConditionalPublicationOutcome, reconcile(intent))

    def _validate_target(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome | None:
        try:
            stored = self._store.get(
                intent.dataset_version.dataset_id,
                intent.dataset_version.version_id,
            )
            if stored.identity != intent.dataset_version.identity:
                raise ValueError("Rollback target identity does not match stored DatasetVersion.")
            self._store.read(stored)
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            return ConditionalPublicationOutcome(
                intent=intent,
                status=ConditionalPublicationStatus.FAILED,
                completed_at=self._completed_at(intent),
                snapshot=self._publisher.inspect(intent.dataset_id),
                failure=FailureEvidence(
                    error_code="governance.rollback.target_invalid",
                    category=FailureCategory.INTEGRITY,
                    retryability=Retryability.NON_RETRYABLE,
                    uncertainty=OutcomeUncertainty.KNOWN,
                    ingestion_run_id=intent.ingestion_run_id,
                    correlation_id=intent.correlation.correlation_id,
                    source_component="governance.rollback",
                    message_summary=(
                        "Rollback target must already exist and pass integrity verification: "
                        f"{type(exc).__name__}."
                    ),
                ),
            )
        return None

    def _ensure_rollback_registered(self, intent: PublicationIntent) -> None:
        existing = self._ledger.get_operation(intent.operation_id)
        if existing is not None:
            existing.assert_same_intent_as(intent)
            if not operation_is_rollback(self._ledger, intent.operation_id):
                raise ValueError(
                    "PublicationOperationId is already registered as a non-rollback operation."
                )
            return

        requested = PublicationLifecycleEvent(
            event_id=f"{intent.operation_id}:{PublicationLifecycleEventType.ROLLBACK_REQUESTED.value}",
            event_type=PublicationLifecycleEventType.ROLLBACK_REQUESTED,
            dataset_id=intent.dataset_id,
            occurred_at=self._completed_at(intent),
            operation_id=intent.operation_id,
            dataset_version=intent.dataset_version,
            previous_revision=intent.expected_revision,
        )
        transaction = getattr(self._ledger, "transaction", None)
        if callable(transaction):
            with transaction() as ledger:
                ledger.register(intent)
                ledger.append(requested)
            return
        self._ledger.register(intent)
        self._ledger.append(requested)

    def _completed_at(self, intent: PublicationIntent) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("GovernedRollbackService clock must return aware datetime.")
        return max(value, intent.requested_at)


def operation_is_rollback(
    ledger: PublicationLedger,
    operation_id: PublicationOperationId,
) -> bool:
    """Return whether durable lifecycle history classifies an operation as rollback."""
    if not isinstance(ledger, PublicationLedger):
        raise TypeError("operation_is_rollback ledger must satisfy PublicationLedger.")
    if not isinstance(operation_id, PublicationOperationId):
        raise TypeError("operation_is_rollback requires PublicationOperationId.")
    reader = ledger if isinstance(ledger, _LifecycleEventReader) else None
    if reader is None:
        return False
    return any(
        event.event_type is PublicationLifecycleEventType.ROLLBACK_REQUESTED
        for event in reader.list_events(operation_id)
    )


__all__ = ["GovernedRollbackService"]
