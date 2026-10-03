"""Additive lifecycle-governance ports for PyIngestKit 2.1."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    ConditionalPublicationOutcome,
    DatasetVersionDeletionReconciliationResult,
    DatasetVersionDeletionResult,
    GarbageCollectionPlanId,
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationOperationId,
    PublicationSnapshot,
)


@runtime_checkable
class PublicationLedger(Protocol):
    """Append-only durable evidence and operation lookup for governance."""

    def register(self, intent: PublicationIntent) -> PublicationIntent: ...

    def append(self, event: PublicationLifecycleEvent) -> None: ...

    def get_operation(self, operation_id: PublicationOperationId) -> PublicationIntent | None: ...

    def list_operations(self, dataset_id: str) -> tuple[PublicationIntent, ...]: ...

    def list_unresolved(
        self,
        dataset_id: str | None = None,
    ) -> tuple[PublicationIntent, ...]: ...


@runtime_checkable
class ConditionalDatasetPublisher(Protocol):
    """Compare-and-swap publication capability additive to DatasetPublisher."""

    def inspect(self, dataset_id: str) -> PublicationSnapshot: ...

    def compare_and_publish(
        self,
        intent: PublicationIntent,
    ) -> ConditionalPublicationOutcome: ...


@runtime_checkable
class DatasetVersionGarbageCollector(Protocol):
    """Destructive lifecycle capability kept separate from DatasetVersionStore."""

    def delete(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        expected_evidence: str,
        requested_at: datetime,
    ) -> DatasetVersionDeletionResult: ...

    def reconcile_delete(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        reconciled_at: datetime,
    ) -> DatasetVersionDeletionReconciliationResult: ...
