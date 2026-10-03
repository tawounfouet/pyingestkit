from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from pyingestkit.adapters.filesystem import (
    FileConditionalDatasetPublisher,
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
)
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance import (
    ConditionalPublicationStatus,
    PublicationIntent,
    PublicationOperationId,
    PublicationRevision,
)
from pyingestkit.ports.governance import ConditionalDatasetPublisher

_NOW = datetime(2026, 10, 3, 21, 0, tzinfo=UTC)
_DATASET_ID = "governance.filesystem_contract"


def _put_version(
    store: FileDatasetVersionStore,
    tmp_path: Path,
    *,
    name: str,
    value: str,
):
    source = tmp_path / f"{name}.csv"
    source.write_text(f"id,value\n1,{value}\n", encoding="utf-8")
    run_id = IngestionRunId.new()
    materializer = FileCsvDatasetVersionMaterializerV2(allowed_roots=(tmp_path,))
    version = materializer.materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id=_DATASET_ID,
            resource=ResourceReference(
                namespace="governance.test",
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
    requested_at: datetime = _NOW,
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


def test_filesystem_conditional_publisher_satisfies_frozen_port(tmp_path: Path) -> None:
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
        clock=lambda: _NOW,
    )
    assert isinstance(publisher, ConditionalDatasetPublisher)
    assert publisher.inspect(_DATASET_ID).revision == PublicationRevision.initial()


def test_governed_pointer_remains_readable_by_frozen_dataset_publisher(
    tmp_path: Path,
) -> None:
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    reference = _put_version(store, tmp_path, name="v1", value="a")
    ledger = MemoryPublicationLedger()
    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: _NOW,
    )

    result = publisher.compare_and_publish(
        _intent(reference, PublicationRevision.initial())
    )

    assert result.status is ConditionalPublicationStatus.SUCCEEDED
    assert result.snapshot is not None
    frozen_reader = store.get_published(_DATASET_ID)
    assert frozen_reader is not None
    assert frozen_reader.version.identity == reference.identity


def test_legacy_pointer_can_be_bootstrapped_then_governed_without_shape_break(
    tmp_path: Path,
) -> None:
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    v1 = _put_version(store, tmp_path, name="legacy-v1", value="a")
    v2 = _put_version(store, tmp_path, name="legacy-v2", value="b")
    legacy_run = IngestionRunId.new()
    store.publish(v1, ingestion_run_id=legacy_run, published_at=_NOW)

    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
        clock=lambda: _NOW + timedelta(seconds=1),
    )
    bootstrap = publisher.inspect(_DATASET_ID)
    assert bootstrap.published_dataset is not None
    assert bootstrap.revision.is_initial is False

    result = publisher.compare_and_publish(
        _intent(
            v2,
            bootstrap.revision,
            requested_at=_NOW + timedelta(seconds=1),
        )
    )
    assert result.status is ConditionalPublicationStatus.SUCCEEDED
    assert store.get_published(_DATASET_ID) is not None
    assert store.get_published(_DATASET_ID).version.identity == v2.identity


def test_aba_changes_revision_even_when_content_returns_to_old_version(
    tmp_path: Path,
) -> None:
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    v1 = _put_version(store, tmp_path, name="aba-v1", value="a")
    v2 = _put_version(store, tmp_path, name="aba-v2", value="b")
    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
        clock=lambda: _NOW + timedelta(seconds=10),
    )

    first = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial())
    )
    assert first.snapshot is not None
    second = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision)
    )
    assert second.snapshot is not None
    third = publisher.compare_and_publish(
        _intent(v1, second.snapshot.revision)
    )
    assert third.snapshot is not None

    assert third.snapshot.published_dataset is not None
    assert third.snapshot.published_dataset.version.identity == v1.identity
    assert third.snapshot.revision != first.snapshot.revision

    stale = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision)
    )
    assert stale.status is ConditionalPublicationStatus.CONFLICT
    assert publisher.inspect(_DATASET_ID).revision == third.snapshot.revision


def test_crash_before_replace_keeps_prior_pointer_readable(tmp_path: Path) -> None:
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    v1 = _put_version(store, tmp_path, name="before-v1", value="a")
    v2 = _put_version(store, tmp_path, name="before-v2", value="b")
    ledger = MemoryPublicationLedger()
    stable = FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: _NOW,
    )
    first = stable.compare_and_publish(
        _intent(v1, PublicationRevision.initial())
    )
    assert first.snapshot is not None

    def inject(phase: str) -> None:
        if phase == "before_replace":
            raise OSError("simulated crash before replace")

    failing = FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=1),
        fault_injector=inject,
    )
    outcome = failing.compare_and_publish(
        _intent(
            v2,
            first.snapshot.revision,
            requested_at=_NOW + timedelta(seconds=1),
        )
    )

    assert outcome.status is ConditionalPublicationStatus.FAILED
    current = stable.inspect(_DATASET_ID)
    assert current.revision == first.snapshot.revision
    assert current.published_dataset is not None
    assert current.published_dataset.version.identity == v1.identity


def test_unknown_after_replace_requires_reconciliation_and_never_republishes(
    tmp_path: Path,
) -> None:
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    reference = _put_version(store, tmp_path, name="unknown-v1", value="a")
    ledger = MemoryPublicationLedger()

    def inject(phase: str) -> None:
        if phase == "after_replace":
            raise OSError("simulated acknowledgement loss")

    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: _NOW,
        fault_injector=inject,
    )
    intent = _intent(reference, PublicationRevision.initial())
    outcome = publisher.compare_and_publish(intent)

    assert outcome.status is ConditionalPublicationStatus.UNKNOWN_OUTCOME
    assert outcome.failure is not None
    assert outcome.failure.reconciliation_required is True
    assert ledger.list_unresolved(_DATASET_ID) == (intent,)

    reconciler = FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=1),
    )
    reconciled = reconciler.reconcile(intent)
    assert reconciled.status is ConditionalPublicationStatus.SUCCEEDED
    assert reconciled.snapshot is not None
    assert reconciled.snapshot.published_dataset is not None
    assert reconciled.snapshot.published_dataset.version.identity == reference.identity
    assert ledger.list_unresolved(_DATASET_ID) == ()
