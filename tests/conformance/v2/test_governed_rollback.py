from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pyingestkit.adapters.filesystem import (
    FileConditionalDatasetPublisher,
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
)
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.governance import (
    ConditionalPublicationStatus,
    PublicationIntent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, OutcomeUncertainty
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance.rollback import GovernedRollbackService

_NOW = datetime(2026, 10, 4, 3, 0, tzinfo=UTC)
_DATASET_ID = "governance.filesystem_rollback"


def _put_version(
    store: FileDatasetVersionStore,
    workspace: Path,
    *,
    name: str,
    value: str,
):
    source = workspace / f"{name}.csv"
    source.write_text(f"id,value\n1,{value}\n", encoding="utf-8")
    run_id = IngestionRunId.new()
    version = FileCsvDatasetVersionMaterializerV2(
        allowed_roots=(workspace,),
    ).materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id=_DATASET_ID,
            resource=ResourceReference(
                namespace="rollback.test",
                resource_id=name,
                locator=source.resolve().as_uri(),
                media_type="text/csv",
                format="csv",
            ),
            ingestion_run_id=run_id,
            created_at=_NOW,
        )
    )
    return store.put(version)


def _intent(
    reference,
    expected_revision: PublicationRevision,
    *,
    requested_at: datetime,
) -> PublicationIntent:
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=expected_revision,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=requested_at,
    )


def _environment(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    ledger = MemoryPublicationLedger()
    return workspace, store, ledger


def _publisher(store, ledger, when, *, fault_injector=None):
    return FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: when,
        fault_injector=fault_injector,
    )


def test_filesystem_rollback_publishes_existing_version_and_advances_revision(
    tmp_path: Path,
) -> None:
    workspace, store, ledger = _environment(tmp_path)
    v1 = _put_version(store, workspace, name="v1", value="one")
    v2 = _put_version(store, workspace, name="v2", value="two")

    publisher = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    first = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert first.snapshot is not None
    second = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision, requested_at=_NOW)
    )
    assert second.snapshot is not None

    immutable_before = store.read(v1)
    rollback_intent = _intent(
        v1,
        second.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    service = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=3)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=2),
    )
    outcome = service.rollback(rollback_intent)

    assert outcome.status is ConditionalPublicationStatus.SUCCEEDED
    assert outcome.snapshot is not None
    assert outcome.snapshot.published_dataset is not None
    assert outcome.snapshot.published_dataset.version.identity == v1.identity
    assert outcome.snapshot.revision != second.snapshot.revision
    assert store.read(v1) == immutable_before

    events = ledger.list_events(rollback_intent.operation_id)
    assert [event.event_type for event in events] == [
        PublicationLifecycleEventType.ROLLBACK_REQUESTED,
        PublicationLifecycleEventType.ROLLBACK_COMMITTED,
    ]


def test_filesystem_stale_rollback_conflicts_without_mutating_target_bytes(
    tmp_path: Path,
) -> None:
    workspace, store, ledger = _environment(tmp_path)
    v1 = _put_version(store, workspace, name="v1", value="one")
    v2 = _put_version(store, workspace, name="v2", value="two")
    v3 = _put_version(store, workspace, name="v3", value="three")

    publisher = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    first = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert first.snapshot is not None
    second = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision, requested_at=_NOW)
    )
    assert second.snapshot is not None

    stale_intent = _intent(
        v1,
        second.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    newer = publisher.compare_and_publish(
        _intent(v3, second.snapshot.revision, requested_at=_NOW + timedelta(seconds=2))
    )
    assert newer.snapshot is not None

    immutable_before = store.read(v1)
    service = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=3)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=3),
    )
    outcome = service.rollback(stale_intent)

    assert outcome.status is ConditionalPublicationStatus.CONFLICT
    current = publisher.inspect(_DATASET_ID)
    assert current.published_dataset is not None
    assert current.published_dataset.version.identity == v3.identity
    assert store.read(v1) == immutable_before

    events = ledger.list_events(stale_intent.operation_id)
    assert [event.event_type for event in events] == [
        PublicationLifecycleEventType.ROLLBACK_REQUESTED,
        PublicationLifecycleEventType.PUBLICATION_CONFLICT,
    ]


def test_filesystem_repeated_rollback_to_same_version_is_new_revision(
    tmp_path: Path,
) -> None:
    workspace, store, ledger = _environment(tmp_path)
    v1 = _put_version(store, workspace, name="v1", value="one")
    v2 = _put_version(store, workspace, name="v2", value="two")

    publisher = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    first = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert first.snapshot is not None
    current = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision, requested_at=_NOW)
    )
    assert current.snapshot is not None

    service = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=3)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=2),
    )
    first_rollback = service.rollback(
        _intent(v1, current.snapshot.revision, requested_at=_NOW + timedelta(seconds=2))
    )
    assert first_rollback.snapshot is not None

    second_intent = _intent(
        v1,
        first_rollback.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=4),
    )
    second_service = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=5)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=4),
    )
    second_rollback = second_service.rollback(second_intent)

    assert second_rollback.status is ConditionalPublicationStatus.SUCCEEDED
    assert second_rollback.snapshot is not None
    assert second_rollback.snapshot.revision != first_rollback.snapshot.revision
    assert second_rollback.snapshot.published_dataset is not None
    assert second_rollback.snapshot.published_dataset.version.identity == v1.identity


def test_filesystem_missing_rollback_target_fails_before_lifecycle_admission(
    tmp_path: Path,
) -> None:
    workspace, store, ledger = _environment(tmp_path)
    v1 = _put_version(store, workspace, name="v1", value="one")
    publisher = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    current = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert current.snapshot is not None

    missing = replace(
        v1,
        version_id="sha256-" + ("f" * 64),
        locator=None,
    )
    intent = _intent(
        missing,
        current.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    service = GovernedRollbackService(
        store=store,
        publisher=publisher,
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=2),
    )
    outcome = service.rollback(intent)

    assert outcome.status is ConditionalPublicationStatus.FAILED
    assert outcome.failure is not None
    assert outcome.failure.error_code == "governance.rollback.target_invalid"
    assert ledger.get_operation(intent.operation_id) is None
    still_current = publisher.inspect(_DATASET_ID)
    assert still_current.revision == current.snapshot.revision
    assert still_current.published_dataset is not None
    assert still_current.published_dataset.version.identity == v1.identity


def test_filesystem_unknown_rollback_reconciles_without_blind_retry(
    tmp_path: Path,
) -> None:
    workspace, store, ledger = _environment(tmp_path)
    v1 = _put_version(store, workspace, name="v1", value="one")
    v2 = _put_version(store, workspace, name="v2", value="two")

    stable = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    first = stable.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert first.snapshot is not None
    current = stable.compare_and_publish(
        _intent(v2, first.snapshot.revision, requested_at=_NOW)
    )
    assert current.snapshot is not None

    def lose_acknowledgement(phase: str) -> None:
        if phase == "after_replace":
            raise OSError("simulated rollback acknowledgement loss")

    uncertain_publisher = _publisher(
        store,
        ledger,
        _NOW + timedelta(seconds=3),
        fault_injector=lose_acknowledgement,
    )
    intent = _intent(
        v1,
        current.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    service = GovernedRollbackService(
        store=store,
        publisher=uncertain_publisher,
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=2),
    )
    uncertain = service.rollback(intent)

    assert uncertain.status is ConditionalPublicationStatus.UNKNOWN_OUTCOME
    assert uncertain.failure is not None
    assert uncertain.failure.uncertainty is OutcomeUncertainty.REQUIRES_RECONCILIATION
    assert ledger.list_unresolved(_DATASET_ID) == (intent,)

    reconciler = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=4)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=4),
    )
    reconciled = reconciler.reconcile(intent)

    assert reconciled.status is ConditionalPublicationStatus.SUCCEEDED
    assert reconciled.snapshot is not None
    assert reconciled.snapshot.published_dataset is not None
    assert reconciled.snapshot.published_dataset.version.identity == v1.identity
    assert ledger.list_unresolved(_DATASET_ID) == ()
    assert [event.event_type for event in ledger.list_events(intent.operation_id)] == [
        PublicationLifecycleEventType.ROLLBACK_REQUESTED,
        PublicationLifecycleEventType.PUBLICATION_OUTCOME_UNKNOWN,
        PublicationLifecycleEventType.ROLLBACK_COMMITTED,
    ]
