"""Shared guarded-GC mechanics for PyIngestKit 2.1 LOT-27."""

from __future__ import annotations

import hashlib
from datetime import datetime

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    GarbageCollectionPlan,
    GarbageCollectionPlanId,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
)
from pyingestkit.domain.runtime import (
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import CorrelationId, IngestionRunId
from pyingestkit.domain.shared.validation import validate_aware_datetime
from pyingestkit.governance.retention import RetentionPlanner, RetentionStateLoader
from pyingestkit.ports.governance import PublicationLedger


class GarbageCollectionGuardError(RuntimeError):
    """Controlled fail-closed guard rejection before destructive I/O."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary


class GarbageCollectionPlanGuard:
    """Bind destructive operations to one immutable, currently valid plan."""

    def __init__(
        self,
        *,
        plan: GarbageCollectionPlan,
        state_loader: RetentionStateLoader,
    ) -> None:
        if not isinstance(plan, GarbageCollectionPlan):
            raise TypeError("GarbageCollectionPlanGuard plan must be GarbageCollectionPlan.")
        if not isinstance(state_loader, RetentionStateLoader):
            raise TypeError(
                "GarbageCollectionPlanGuard state_loader must be RetentionStateLoader."
            )
        self._plan = plan
        self._state_loader = state_loader
        self._candidate_ids = {reference.identity for reference in plan.candidate_versions}

    @property
    def plan(self) -> GarbageCollectionPlan:
        return self._plan

    def validate_bound_candidate(
        self,
        reference: DatasetVersionReference,
        *,
        plan_id: GarbageCollectionPlanId,
        expected_evidence: str,
    ) -> None:
        if not isinstance(reference, DatasetVersionReference):
            raise GarbageCollectionGuardError(
                "governance.gc.invalid_reference",
                "Garbage collection requires DatasetVersionReference.",
            )
        if not isinstance(plan_id, GarbageCollectionPlanId):
            raise GarbageCollectionGuardError(
                "governance.gc.invalid_plan_id",
                "Garbage collection requires GarbageCollectionPlanId.",
            )
        if plan_id != self._plan.plan_id:
            raise GarbageCollectionGuardError(
                "governance.gc.plan_mismatch",
                "Garbage-collection request does not match the bound plan.",
            )
        if not isinstance(expected_evidence, str) or not expected_evidence.strip():
            raise GarbageCollectionGuardError(
                "governance.gc.invalid_evidence",
                "Garbage-collection expected evidence must be non-blank.",
            )
        if expected_evidence != self._plan.evidence_fingerprint:
            raise GarbageCollectionGuardError(
                "governance.gc.plan_evidence_mismatch",
                "Garbage-collection request evidence does not match the bound plan.",
            )
        if reference.dataset_id != self._plan.dataset_id:
            raise GarbageCollectionGuardError(
                "governance.gc.dataset_mismatch",
                "Garbage-collection candidate belongs to another dataset.",
            )
        if reference.identity not in self._candidate_ids:
            raise GarbageCollectionGuardError(
                "governance.gc.not_candidate",
                "Dataset version is not a candidate in the bound garbage-collection plan.",
            )

    def validate_current_evidence(self) -> None:
        state = self._state_loader.capture(self._plan.dataset_id)
        current_evidence = RetentionPlanner.evidence_fingerprint(
            state,
            policy=self._plan.policy,
            created_at=self._plan.created_at,
        )
        if current_evidence != self._plan.evidence_fingerprint:
            raise GarbageCollectionGuardError(
                "governance.gc.stale_plan",
                "Lifecycle evidence changed after garbage-collection planning.",
            )
        current_plan = RetentionPlanner.plan(
            state,
            policy=self._plan.policy,
            created_at=self._plan.created_at,
            plan_id=self._plan.plan_id,
        )
        if current_plan.evidence_fingerprint != self._plan.evidence_fingerprint:
            raise GarbageCollectionGuardError(
                "governance.gc.stale_plan",
                "Garbage-collection plan no longer matches current lifecycle evidence.",
            )


def gc_failure(
    *,
    plan_id: GarbageCollectionPlanId,
    code: str,
    category: FailureCategory,
    retryability: Retryability,
    uncertainty: OutcomeUncertainty,
    source_component: str,
    summary: str,
    occurred_at: datetime,
) -> FailureEvidence:
    validate_aware_datetime(occurred_at, "GC failure occurred_at")
    return FailureEvidence(
        error_code=code,
        category=category,
        retryability=retryability,
        uncertainty=uncertainty,
        ingestion_run_id=IngestionRunId(plan_id.value),
        correlation_id=CorrelationId(plan_id.value),
        source_component=source_component,
        message_summary=summary,
        occurred_at=occurred_at,
        details=(("plan_id", str(plan_id)),),
    )


def append_gc_event(
    ledger: PublicationLedger,
    *,
    event_type: PublicationLifecycleEventType,
    reference: DatasetVersionReference,
    plan_id: GarbageCollectionPlanId,
    occurred_at: datetime,
    expected_evidence: str,
    failure: FailureEvidence | None = None,
    phase: str = "execution",
) -> None:
    if not isinstance(ledger, PublicationLedger):
        raise TypeError("GC event ledger must satisfy PublicationLedger.")
    validate_aware_datetime(occurred_at, "GC event occurred_at")
    digest = hashlib.sha256(
        (
            f"{plan_id}\0"
            f"{reference.dataset_id}\0"
            f"{reference.version_id}\0"
            f"{event_type.value}\0"
            f"{phase}\0"
            f"{occurred_at.isoformat()}"
        ).encode("utf-8")
    ).hexdigest()
    ledger.append(
        PublicationLifecycleEvent(
            event_id=f"gc:{digest}",
            event_type=event_type,
            dataset_id=reference.dataset_id,
            occurred_at=occurred_at,
            dataset_version=reference,
            failure=failure,
            metadata=(
                ("plan_id", str(plan_id)),
                ("expected_evidence", expected_evidence),
                ("phase", phase),
            ),
        )
    )


__all__ = [
    "GarbageCollectionGuardError",
    "GarbageCollectionPlanGuard",
    "append_gc_event",
    "gc_failure",
]
