from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.datasets.publication import PublishedDataset
from pyingestkit.domain.governance import (
    PublicationIntent,
    PublicationOperationId,
    PublicationRevision,
    PublicationSnapshot,
    RetentionPolicy,
    VersionHold,
)
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance.retention import RetentionPlanner, RetentionState

_NOW = datetime(2026, 10, 4, 1, 0, tzinfo=UTC)
_DATASET = "retention.demo"


def _reference(index: int, *, age_days: int) -> DatasetVersionReference:
    return DatasetVersionReference(
        dataset_id=_DATASET,
        version_id=f"sha256-{index:064x}",
        created_at=_NOW - timedelta(days=age_days),
        schema_fingerprint=f"schema-{index}",
        content_fingerprint=f"sha256-{index:064x}",
    )


def _current(reference: DatasetVersionReference) -> PublicationSnapshot:
    return PublicationSnapshot(
        dataset_id=_DATASET,
        revision=PublicationRevision.new(),
        published_dataset=PublishedDataset(
            dataset_id=_DATASET,
            version=reference,
            published_at=_NOW,
            published_from_run_id=IngestionRunId.new(),
        ),
    )


def _intent(reference: DatasetVersionReference) -> PublicationIntent:
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=PublicationRevision.new(),
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=_NOW,
    )


def test_retention_planner_protects_current_hold_unresolved_and_unverified() -> None:
    newest = _reference(5, age_days=1)
    unresolved = _reference(4, age_days=2)
    held = _reference(3, age_days=3)
    corrupt = _reference(2, age_days=4)
    candidate = _reference(1, age_days=5)
    inventory = (newest, unresolved, held, corrupt, candidate)

    state = RetentionState(
        dataset_id=_DATASET,
        inventory=inventory,
        current=_current(newest),
        active_holds=(VersionHold(held, held_at=_NOW - timedelta(hours=1), reason="legal"),),
        unresolved_operations=(_intent(unresolved),),
        verified_versions=(newest, unresolved, held, candidate),
    )
    plan = RetentionPlanner.plan(
        state,
        policy=RetentionPolicy(keep_last=1),
        created_at=_NOW,
    )

    assert tuple(reference.identity for reference in plan.candidate_versions) == (
        candidate.identity,
    )
    assert {reference.identity for reference in plan.protected_versions} == {
        newest.identity,
        unresolved.identity,
        held.identity,
        corrupt.identity,
    }


def test_retention_planner_min_age_is_deterministic_and_missing_time_is_protected() -> None:
    recent = _reference(4, age_days=1)
    old_a = _reference(3, age_days=10)
    old_b = _reference(2, age_days=20)
    unknown_time = DatasetVersionReference(
        dataset_id=_DATASET,
        version_id=f"sha256-{1:064x}",
    )
    inventory = (recent, old_a, old_b, unknown_time)
    state = RetentionState(
        dataset_id=_DATASET,
        inventory=inventory,
        current=PublicationSnapshot(
            dataset_id=_DATASET,
            revision=PublicationRevision.initial(),
        ),
        active_holds=(),
        unresolved_operations=(),
        verified_versions=inventory,
    )
    policy = RetentionPolicy(keep_last=1, min_age_seconds=7 * 24 * 60 * 60)

    first = RetentionPlanner.plan(state, policy=policy, created_at=_NOW)
    second = RetentionPlanner.plan(
        state,
        policy=policy,
        created_at=_NOW,
        plan_id=first.plan_id,
    )

    assert first.evidence_fingerprint == second.evidence_fingerprint
    assert tuple(reference.identity for reference in first.candidate_versions) == (
        old_a.identity,
        old_b.identity,
    )
    assert recent.identity in {reference.identity for reference in first.protected_versions}
    assert unknown_time.identity in {
        reference.identity for reference in first.protected_versions
    }


def test_plan_fingerprint_changes_when_hold_or_unresolved_state_changes() -> None:
    newest = _reference(3, age_days=1)
    old = _reference(2, age_days=10)
    other = _reference(1, age_days=20)
    base = RetentionState(
        dataset_id=_DATASET,
        inventory=(newest, old, other),
        current=_current(newest),
        active_holds=(),
        unresolved_operations=(),
        verified_versions=(newest, old, other),
    )
    held = RetentionState(
        dataset_id=_DATASET,
        inventory=base.inventory,
        current=base.current,
        active_holds=(VersionHold(old, held_at=_NOW, reason="investigation"),),
        unresolved_operations=(),
        verified_versions=base.verified_versions,
    )
    unresolved = RetentionState(
        dataset_id=_DATASET,
        inventory=base.inventory,
        current=base.current,
        active_holds=(),
        unresolved_operations=(_intent(other),),
        verified_versions=base.verified_versions,
    )
    policy = RetentionPolicy(keep_last=1)

    fingerprints = {
        RetentionPlanner.evidence_fingerprint(base, policy=policy, created_at=_NOW),
        RetentionPlanner.evidence_fingerprint(held, policy=policy, created_at=_NOW),
        RetentionPlanner.evidence_fingerprint(unresolved, policy=policy, created_at=_NOW),
    }
    assert len(fingerprints) == 3


def test_memory_hold_repository_emits_lifecycle_events_and_releases_idempotently() -> None:
    ledger = MemoryPublicationLedger()
    reference = _reference(1, age_days=5)
    hold = VersionHold(reference, held_at=_NOW, reason="audit")

    assert ledger.place_hold(hold) == hold
    assert ledger.place_hold(hold) == hold
    assert ledger.list_active_holds(_DATASET) == (hold,)

    events = ledger.list_events(dataset_id=_DATASET)
    assert [event.event_type.value for event in events] == ["hold_placed"]

    released_at = _NOW + timedelta(minutes=5)
    assert ledger.release_hold(reference, released_at=released_at) is True
    assert ledger.release_hold(reference, released_at=released_at) is False
    assert ledger.list_active_holds(_DATASET) == ()

    events = ledger.list_events(dataset_id=_DATASET)
    assert [event.event_type.value for event in events] == [
        "hold_placed",
        "hold_released",
    ]
