"""Guarded S3 DatasetVersion garbage collection for LOT-27."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime

from pyingestkit.adapters.s3.dataset_version_store import S3DatasetVersionStoreV2
from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    DatasetVersionDeletionReconciliationResult,
    DatasetVersionDeletionReconciliationStatus,
    DatasetVersionDeletionResult,
    DatasetVersionDeletionStatus,
    GarbageCollectionPlanId,
    PublicationLifecycleEventType,
)
from pyingestkit.domain.runtime import (
    FailureCategory,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared.validation import validate_aware_datetime
from pyingestkit.governance.gc import (
    GarbageCollectionGuardError,
    GarbageCollectionPlanGuard,
    append_gc_event,
    gc_failure,
)
from pyingestkit.ports.governance import DatasetVersionGarbageCollector, PublicationLedger


class S3DatasetVersionGarbageCollector(DatasetVersionGarbageCollector):
    """Delete only canonical bucket/prefix keys authorized by one live GC plan."""

    def __init__(
        self,
        *,
        store: S3DatasetVersionStoreV2,
        ledger: PublicationLedger,
        guard: GarbageCollectionPlanGuard,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        if not isinstance(store, S3DatasetVersionStoreV2):
            raise TypeError(
                "S3DatasetVersionGarbageCollector store must be S3DatasetVersionStoreV2."
            )
        if not isinstance(ledger, PublicationLedger):
            raise TypeError(
                "S3DatasetVersionGarbageCollector ledger must satisfy PublicationLedger."
            )
        if not isinstance(guard, GarbageCollectionPlanGuard):
            raise TypeError(
                "S3DatasetVersionGarbageCollector guard must be GarbageCollectionPlanGuard."
            )
        self._store = store
        self._ledger = ledger
        self._guard = guard
        self._fault_injector = fault_injector

    def delete(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        expected_evidence: str,
        requested_at: datetime,
    ) -> DatasetVersionDeletionResult:
        validate_aware_datetime(requested_at, "S3 GC requested_at")
        try:
            self._guard.validate_bound_candidate(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
            )
        except GarbageCollectionGuardError as exc:
            return self._failed(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code=exc.code,
                category=FailureCategory.CONFLICT,
                summary=exc.summary,
            )

        state = self._canonical_state(reference)
        if state == "absent":
            self._append_success_event(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                occurred_at=requested_at,
            )
            return DatasetVersionDeletionResult(
                dataset_version=reference,
                status=DatasetVersionDeletionStatus.ALREADY_ABSENT,
                completed_at=requested_at,
                provider_operation_reference=self._provider_reference(reference, plan_id),
            )
        if state != "present":
            return self._failed(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.s3.gc.invalid_canonical_state",
                category=FailureCategory.INTEGRITY,
                summary="S3 dataset version is incomplete, unsafe or non-canonical.",
            )

        try:
            self._guard.validate_current_evidence()
        except GarbageCollectionGuardError as exc:
            return self._failed(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code=exc.code,
                category=FailureCategory.CONFLICT,
                summary=exc.summary,
            )

        try:
            append_gc_event(
                self._ledger,
                event_type=PublicationLifecycleEventType.GC_DELETE_REQUESTED,
                reference=reference,
                plan_id=plan_id,
                occurred_at=requested_at,
                expected_evidence=expected_evidence,
            )
        except Exception as exc:  # noqa: BLE001 - no provider side effect has happened yet
            return self._failed(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.s3.gc.request_evidence_failed",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                summary=f"GC request evidence could not be persisted: {type(exc).__name__}.",
                append_event=False,
            )

        try:
            self._inject("before_delete")
        except Exception as exc:  # noqa: BLE001 - injected pre-side-effect failure
            return self._failed(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.s3.gc.pre_delete_failed",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                summary=f"S3 GC failed before deletion: {type(exc).__name__}.",
            )

        metadata_key, snapshot_key = self._version_keys(reference)
        try:
            self._store._objects.delete(metadata_key)
            self._inject("after_metadata_delete")
            self._store._objects.delete(snapshot_key)
            self._inject("after_delete")
        except Exception as exc:  # noqa: BLE001 - one or both provider deletes may have committed
            return self._unknown(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.s3.gc.unknown_outcome",
                summary=f"S3 deletion outcome is uncertain: {type(exc).__name__}.",
            )

        try:
            self._append_success_event(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                occurred_at=requested_at,
            )
        except Exception:  # noqa: BLE001 - provider delete committed but ledger outcome is uncertain
            return self._unknown(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.s3.gc.ledger_outcome_unknown",
                summary="S3 version was deleted but durable GC evidence is uncertain.",
                append_event=False,
            )

        return DatasetVersionDeletionResult(
            dataset_version=reference,
            status=DatasetVersionDeletionStatus.DELETED,
            completed_at=requested_at,
            provider_operation_reference=self._provider_reference(reference, plan_id),
        )

    def reconcile_delete(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        reconciled_at: datetime,
    ) -> DatasetVersionDeletionReconciliationResult:
        validate_aware_datetime(reconciled_at, "S3 GC reconciled_at")
        try:
            self._guard.validate_bound_candidate(
                reference,
                plan_id=plan_id,
                expected_evidence=self._guard.plan.evidence_fingerprint,
            )
        except GarbageCollectionGuardError as exc:
            failure = gc_failure(
                plan_id=plan_id,
                code=exc.code,
                category=FailureCategory.CONFLICT,
                retryability=Retryability.NON_RETRYABLE,
                uncertainty=OutcomeUncertainty.KNOWN,
                source_component="governance.s3.gc",
                summary=exc.summary,
                occurred_at=reconciled_at,
            )
            return DatasetVersionDeletionReconciliationResult(
                dataset_version=reference,
                status=DatasetVersionDeletionReconciliationStatus.CONFLICT,
                reconciled_at=reconciled_at,
                failure=failure,
            )

        state = self._canonical_state(reference)
        if state == "absent":
            append_gc_event(
                self._ledger,
                event_type=PublicationLifecycleEventType.GC_DELETE_COMMITTED,
                reference=reference,
                plan_id=plan_id,
                occurred_at=reconciled_at,
                expected_evidence=self._guard.plan.evidence_fingerprint,
                phase="reconciliation",
            )
            return DatasetVersionDeletionReconciliationResult(
                dataset_version=reference,
                status=DatasetVersionDeletionReconciliationStatus.CONFIRMED_DELETED,
                reconciled_at=reconciled_at,
            )
        if state == "present":
            failure = gc_failure(
                plan_id=plan_id,
                code="governance.s3.gc.reconciled_present",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                retryability=Retryability.RETRYABLE,
                uncertainty=OutcomeUncertainty.KNOWN,
                source_component="governance.s3.gc",
                summary="S3 provider truth confirms the dataset version is still present.",
                occurred_at=reconciled_at,
            )
            append_gc_event(
                self._ledger,
                event_type=PublicationLifecycleEventType.GC_DELETE_FAILED,
                reference=reference,
                plan_id=plan_id,
                occurred_at=reconciled_at,
                expected_evidence=self._guard.plan.evidence_fingerprint,
                failure=failure,
                phase="reconciliation",
            )
            return DatasetVersionDeletionReconciliationResult(
                dataset_version=reference,
                status=DatasetVersionDeletionReconciliationStatus.CONFIRMED_PRESENT,
                reconciled_at=reconciled_at,
            )

        failure = gc_failure(
            plan_id=plan_id,
            code="governance.s3.gc.reconciliation_unknown",
            category=FailureCategory.UNKNOWN_OUTCOME,
            retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
            uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
            source_component="governance.s3.gc",
            summary="S3 provider truth is incomplete or inconsistent.",
            occurred_at=reconciled_at,
        )
        append_gc_event(
            self._ledger,
            event_type=PublicationLifecycleEventType.GC_DELETE_OUTCOME_UNKNOWN,
            reference=reference,
            plan_id=plan_id,
            occurred_at=reconciled_at,
            expected_evidence=self._guard.plan.evidence_fingerprint,
            failure=failure,
            phase="reconciliation",
        )
        return DatasetVersionDeletionReconciliationResult(
            dataset_version=reference,
            status=DatasetVersionDeletionReconciliationStatus.UNKNOWN,
            reconciled_at=reconciled_at,
            failure=failure,
        )

    def _canonical_state(self, reference: DatasetVersionReference) -> str:
        metadata_key, snapshot_key = self._version_keys(reference)
        try:
            metadata_head = self._store._objects.head(metadata_key)
            snapshot_head = self._store._objects.head(snapshot_key)
        except RuntimeError:
            return "invalid"
        if metadata_head is None and snapshot_head is None:
            return "absent"
        if metadata_head is None or snapshot_head is None:
            return "invalid"
        try:
            canonical = self._store.get(reference.dataset_id, reference.version_id)
            if reference.locator is not None and reference.locator != canonical.locator:
                return "invalid"
            self._store.read(canonical)
        except (KeyError, RuntimeError, ValueError):
            return "invalid"
        return "present"

    def _version_keys(self, reference: DatasetVersionReference) -> tuple[str, str]:
        return (
            self._store._version_metadata_key(reference.dataset_id, reference.version_id),
            self._store._snapshot_key(reference.dataset_id, reference.version_id),
        )

    def _append_success_event(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        expected_evidence: str,
        occurred_at: datetime,
    ) -> None:
        append_gc_event(
            self._ledger,
            event_type=PublicationLifecycleEventType.GC_DELETE_COMMITTED,
            reference=reference,
            plan_id=plan_id,
            occurred_at=occurred_at,
            expected_evidence=expected_evidence,
        )

    def _failed(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        expected_evidence: str,
        completed_at: datetime,
        code: str,
        category: FailureCategory,
        summary: str,
        append_event: bool = True,
    ) -> DatasetVersionDeletionResult:
        failure = gc_failure(
            plan_id=plan_id,
            code=code,
            category=category,
            retryability=Retryability.NON_RETRYABLE,
            uncertainty=OutcomeUncertainty.KNOWN,
            source_component="governance.s3.gc",
            summary=summary,
            occurred_at=completed_at,
        )
        if append_event:
            append_gc_event(
                self._ledger,
                event_type=PublicationLifecycleEventType.GC_DELETE_FAILED,
                reference=reference,
                plan_id=plan_id,
                occurred_at=completed_at,
                expected_evidence=expected_evidence,
                failure=failure,
            )
        return DatasetVersionDeletionResult(
            dataset_version=reference,
            status=DatasetVersionDeletionStatus.FAILED,
            completed_at=completed_at,
            failure=failure,
            provider_operation_reference=self._provider_reference(reference, plan_id),
        )

    def _unknown(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        expected_evidence: str,
        completed_at: datetime,
        code: str,
        summary: str,
        append_event: bool = True,
    ) -> DatasetVersionDeletionResult:
        failure = gc_failure(
            plan_id=plan_id,
            code=code,
            category=FailureCategory.UNKNOWN_OUTCOME,
            retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
            uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
            source_component="governance.s3.gc",
            summary=summary,
            occurred_at=completed_at,
        )
        if append_event:
            try:
                append_gc_event(
                    self._ledger,
                    event_type=PublicationLifecycleEventType.GC_DELETE_OUTCOME_UNKNOWN,
                    reference=reference,
                    plan_id=plan_id,
                    occurred_at=completed_at,
                    expected_evidence=expected_evidence,
                    failure=failure,
                )
            except Exception:  # noqa: BLE001 - uncertainty evidence is best effort
                pass
        return DatasetVersionDeletionResult(
            dataset_version=reference,
            status=DatasetVersionDeletionStatus.UNKNOWN_OUTCOME,
            completed_at=completed_at,
            failure=failure,
            provider_operation_reference=self._provider_reference(reference, plan_id),
        )

    def _provider_reference(
        self,
        reference: DatasetVersionReference,
        plan_id: GarbageCollectionPlanId,
    ) -> str:
        digest = hashlib.sha256(
            (
                f"{self._store.bucket}\0"
                f"{self._store.prefix}\0"
                f"{reference.dataset_id}\0"
                f"{reference.version_id}"
            ).encode("utf-8")
        ).hexdigest()[:16]
        return f"s3-gc:{digest}:{plan_id}"

    def _inject(self, phase: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(phase)


__all__ = ["S3DatasetVersionGarbageCollector"]
