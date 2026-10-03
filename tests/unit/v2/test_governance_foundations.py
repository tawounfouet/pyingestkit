from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.runtime import (
    CorrelationContext,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance import (
    ConditionalPublicationOutcome,
    ConditionalPublicationStatus,
    DatasetVersionDeletionResult,
    DatasetVersionDeletionStatus,
    GarbageCollectionPlan,
    GarbageCollectionPlanId,
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
    PublicationSnapshot,
    RetentionPolicy,
    VersionHold,
)

_NOW = datetime(2026, 10, 3, 20, 0, tzinfo=UTC)


def _reference(version_id: str = "sha256-" + "1" * 64) -> DatasetVersionReference:
    return DatasetVersionReference(
        dataset_id="customer360.customers",
        version_id=version_id,
        created_at=_NOW,
        schema_fingerprint="schema-1",
        content_fingerprint=version_id,
    )


def _intent(
    *,
    operation_id: PublicationOperationId | None = None,
    reference: DatasetVersionReference | None = None,
    expected_revision: PublicationRevision | None = None,
) -> PublicationIntent:
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=operation_id or PublicationOperationId.new(),
        dataset_version=reference or _reference(),
        expected_revision=expected_revision or PublicationRevision.initial(),
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=_NOW,
    )


def _failure(intent: PublicationIntent, category: FailureCategory) -> FailureEvidence:
    uncertainty = (
        OutcomeUncertainty.REQUIRES_RECONCILIATION
        if category is FailureCategory.UNKNOWN_OUTCOME
        else OutcomeUncertainty.KNOWN
    )
    retryability = (
        Retryability.RETRYABLE_AFTER_RECONCILIATION
        if category is FailureCategory.UNKNOWN_OUTCOME
        else Retryability.NON_RETRYABLE
    )
    return FailureEvidence(
        error_code=f"governance.{category.value}",
        category=category,
        retryability=retryability,
        uncertainty=uncertainty,
        ingestion_run_id=intent.ingestion_run_id,
        correlation_id=intent.correlation.correlation_id,
        source_component="governance",
    )


def test_publication_revision_has_explicit_initial_and_framework_revision() -> None:
    initial = PublicationRevision.initial()
    current = PublicationRevision.new()

    assert initial.is_initial is True
    assert current.is_initial is False
    assert PublicationRevision.parse(str(current)) == current

    with pytest.raises(ValueError):
        PublicationRevision("etag-provider-token")


def test_unpublished_snapshot_requires_initial_revision() -> None:
    snapshot = PublicationSnapshot(
        dataset_id="customer360.customers",
        revision=PublicationRevision.initial(),
    )
    assert snapshot.published_dataset is None

    with pytest.raises(ValueError):
        PublicationSnapshot(
            dataset_id="customer360.customers",
            revision=PublicationRevision.new(),
        )


def test_published_snapshot_requires_non_initial_matching_dataset() -> None:
    reference = _reference()
    run_id = IngestionRunId.new()
    published = PublishedDataset(
        dataset_id=reference.dataset_id,
        version=reference,
        published_at=_NOW,
        published_from_run_id=run_id,
    )

    snapshot = PublicationSnapshot(
        dataset_id=reference.dataset_id,
        revision=PublicationRevision.new(),
        published_dataset=published,
    )
    assert snapshot.published_dataset is published

    with pytest.raises(ValueError):
        PublicationSnapshot(
            dataset_id=reference.dataset_id,
            revision=PublicationRevision.initial(),
            published_dataset=published,
        )


def test_publication_intent_fingerprint_is_idempotent_and_detects_reuse() -> None:
    operation_id = PublicationOperationId.new()
    first = _intent(operation_id=operation_id)
    same = PublicationIntent(
        operation_id=operation_id,
        dataset_version=first.dataset_version,
        expected_revision=first.expected_revision,
        ingestion_run_id=first.ingestion_run_id,
        correlation=first.correlation,
        requested_at=_NOW.replace(hour=21),
    )

    assert first.intent_fingerprint == same.intent_fingerprint
    first.assert_same_intent_as(same)

    changed = PublicationIntent(
        operation_id=operation_id,
        dataset_version=_reference("sha256-" + "2" * 64),
        expected_revision=first.expected_revision,
        ingestion_run_id=first.ingestion_run_id,
        correlation=first.correlation,
        requested_at=_NOW,
    )
    assert first.same_intent_as(changed) is False
    with pytest.raises(ValueError, match="cannot be reused"):
        first.assert_same_intent_as(changed)


def test_lifecycle_event_rejects_credential_like_metadata() -> None:
    with pytest.raises(ValueError, match="credential-like"):
        PublicationLifecycleEvent(
            event_id="event-1",
            event_type=PublicationLifecycleEventType.PUBLICATION_REQUESTED,
            dataset_id="customer360.customers",
            occurred_at=_NOW,
            metadata=(("api_key", "secret"),),
        )


def test_unknown_conditional_outcome_requires_reconciliation_failure() -> None:
    intent = _intent()
    outcome = ConditionalPublicationOutcome(
        intent=intent,
        status=ConditionalPublicationStatus.UNKNOWN_OUTCOME,
        completed_at=_NOW,
        failure=_failure(intent, FailureCategory.UNKNOWN_OUTCOME),
    )
    assert outcome.status is ConditionalPublicationStatus.UNKNOWN_OUTCOME

    with pytest.raises(ValueError, match="UNKNOWN_OUTCOME"):
        ConditionalPublicationOutcome(
            intent=intent,
            status=ConditionalPublicationStatus.UNKNOWN_OUTCOME,
            completed_at=_NOW,
            failure=_failure(intent, FailureCategory.CONFLICT),
        )


def test_retention_policy_is_small_and_fail_closed() -> None:
    assert RetentionPolicy(keep_last=2, min_age_seconds=3600).keep_last == 2

    with pytest.raises(ValueError):
        RetentionPolicy(keep_last=0)
    with pytest.raises(ValueError):
        RetentionPolicy(min_age_seconds=-1)
    with pytest.raises(TypeError):
        RetentionPolicy(keep_last=True)  # type: ignore[arg-type]


def test_version_hold_requires_aware_timestamp() -> None:
    hold = VersionHold(dataset_version=_reference(), held_at=_NOW, reason="operator hold")
    assert hold.dataset_version.dataset_id == "customer360.customers"

    with pytest.raises(ValueError):
        VersionHold(dataset_version=_reference(), held_at=datetime(2026, 10, 3))


def test_gc_plan_keeps_protected_and_candidates_disjoint() -> None:
    protected = _reference("sha256-" + "3" * 64)
    candidate = _reference("sha256-" + "4" * 64)
    plan = GarbageCollectionPlan(
        plan_id=GarbageCollectionPlanId.new(),
        dataset_id=protected.dataset_id,
        created_at=_NOW,
        policy=RetentionPolicy(keep_last=1),
        protected_versions=(protected,),
        candidate_versions=(candidate,),
        evidence_fingerprint="sha256-" + "a" * 64,
    )
    assert plan.candidate_versions == (candidate,)

    with pytest.raises(ValueError, match="disjoint"):
        GarbageCollectionPlan(
            plan_id=GarbageCollectionPlanId.new(),
            dataset_id=protected.dataset_id,
            created_at=_NOW,
            policy=RetentionPolicy(),
            protected_versions=(protected,),
            candidate_versions=(protected,),
            evidence_fingerprint="sha256-" + "b" * 64,
        )


def test_deletion_result_uses_shared_unknown_outcome_semantics() -> None:
    intent = _intent()
    result = DatasetVersionDeletionResult(
        dataset_version=intent.dataset_version,
        status=DatasetVersionDeletionStatus.UNKNOWN_OUTCOME,
        completed_at=_NOW,
        failure=_failure(intent, FailureCategory.UNKNOWN_OUTCOME),
    )
    assert result.status is DatasetVersionDeletionStatus.UNKNOWN_OUTCOME
