"""Guarded filesystem DatasetVersion garbage collection for LOT-27."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from pyingestkit.adapters.filesystem.dataset_version_store import FileDatasetVersionStore
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


class FileDatasetVersionGarbageCollector(DatasetVersionGarbageCollector):
    """Delete only canonical in-root filesystem versions allowed by one live plan."""

    def __init__(
        self,
        *,
        store: FileDatasetVersionStore,
        ledger: PublicationLedger,
        guard: GarbageCollectionPlanGuard,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        if not isinstance(store, FileDatasetVersionStore):
            raise TypeError(
                "FileDatasetVersionGarbageCollector store must be FileDatasetVersionStore."
            )
        if not isinstance(ledger, PublicationLedger):
            raise TypeError(
                "FileDatasetVersionGarbageCollector ledger must satisfy PublicationLedger."
            )
        if not isinstance(guard, GarbageCollectionPlanGuard):
            raise TypeError(
                "FileDatasetVersionGarbageCollector guard must be GarbageCollectionPlanGuard."
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
        validate_aware_datetime(requested_at, "File GC requested_at")
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
                code="governance.filesystem.gc.invalid_canonical_state",
                category=FailureCategory.INTEGRITY,
                summary="Filesystem dataset version is incomplete, unsafe or non-canonical.",
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
        except Exception as exc:  # noqa: BLE001 - no side effect has happened yet
            return self._failed(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.filesystem.gc.request_evidence_failed",
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
                code="governance.filesystem.gc.pre_delete_failed",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                summary=f"Filesystem GC failed before deletion: {type(exc).__name__}.",
            )

        target = self._version_dir(reference)
        try:
            shutil.rmtree(target)
            self._inject("after_delete")
        except Exception as exc:  # noqa: BLE001 - deletion may have partially/fully committed
            return self._unknown(
                reference,
                plan_id=plan_id,
                expected_evidence=expected_evidence,
                completed_at=requested_at,
                code="governance.filesystem.gc.unknown_outcome",
                summary=f"Filesystem deletion outcome is uncertain: {type(exc).__name__}.",
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
                code="governance.filesystem.gc.ledger_outcome_unknown",
                summary="Filesystem version was deleted but durable GC evidence is uncertain.",
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
        validate_aware_datetime(reconciled_at, "File GC reconciled_at")
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
                source_component="governance.filesystem.gc",
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
                code="governance.filesystem.gc.reconciled_present",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                retryability=Retryability.RETRYABLE,
                uncertainty=OutcomeUncertainty.KNOWN,
                source_component="governance.filesystem.gc",
                summary="Filesystem provider truth confirms the dataset version is still present.",
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
            code="governance.filesystem.gc.reconciliation_unknown",
            category=FailureCategory.UNKNOWN_OUTCOME,
            retryability=Retryability.RETRYABLE_AFTER_RECONCILIATION,
            uncertainty=OutcomeUncertainty.REQUIRES_RECONCILIATION,
            source_component="governance.filesystem.gc",
            summary="Filesystem provider truth is incomplete or unsafe.",
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
        target = self._version_dir(reference)
        if target.is_symlink():
            return "invalid"
        if not target.exists():
            return "absent"
        try:
            resolved = target.resolve(strict=True)
        except OSError:
            return "invalid"
        root = self._store.root.resolve(strict=False)
        if not resolved.is_relative_to(root):
            return "invalid"
        try:
            canonical = self._store.get(reference.dataset_id, reference.version_id)
            if reference.locator is not None and reference.locator != canonical.locator:
                return "invalid"
            self._store.read(canonical)
        except (KeyError, OSError, ValueError):
            return "invalid"
        return "present"

    def _version_dir(self, reference: DatasetVersionReference) -> Path:
        return self._store._version_dir(reference.dataset_id, reference.version_id)

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
            source_component="governance.filesystem.gc",
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
            source_component="governance.filesystem.gc",
            summary=summary,
            occurred_at=completed_at,
        )
        if append_event:
            with suppress(Exception):
                append_gc_event(
                    self._ledger,
                    event_type=PublicationLifecycleEventType.GC_DELETE_OUTCOME_UNKNOWN,
                    reference=reference,
                    plan_id=plan_id,
                    occurred_at=completed_at,
                    expected_evidence=expected_evidence,
                    failure=failure,
                )
        return DatasetVersionDeletionResult(
            dataset_version=reference,
            status=DatasetVersionDeletionStatus.UNKNOWN_OUTCOME,
            completed_at=completed_at,
            failure=failure,
            provider_operation_reference=self._provider_reference(reference, plan_id),
        )

    @staticmethod
    def _provider_reference(
        reference: DatasetVersionReference,
        plan_id: GarbageCollectionPlanId,
    ) -> str:
        digest = hashlib.sha256(
            f"{reference.dataset_id}\0{reference.version_id}".encode()
        ).hexdigest()[:16]
        return f"filesystem-gc:{digest}:{plan_id}"

    def _inject(self, phase: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(phase)


__all__ = ["FileDatasetVersionGarbageCollector"]
