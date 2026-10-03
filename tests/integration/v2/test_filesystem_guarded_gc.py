from __future__ import annotations

import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pyingestkit.adapters.filesystem import (
    FileConditionalDatasetPublisher,
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionGarbageCollector,
    FileDatasetVersionStore,
)
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.governance import (
    DatasetVersionDeletionReconciliationStatus,
    DatasetVersionDeletionStatus,
    PublicationIntent,
    PublicationOperationId,
    PublicationRevision,
    RetentionPolicy,
    VersionHold,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, OutcomeUncertainty
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance.gc import GarbageCollectionPlanGuard
from pyingestkit.governance.retention import (
    RetentionPlanner,
    RetentionStateLoader,
    record_retention_plan,
)

_NOW = datetime(2026, 10, 4, 1, 30, tzinfo=UTC)
_DATASET = "governance.file_gc"


def _put_version(
    store: FileDatasetVersionStore,
    workspace: Path,
    *,
    name: str,
    value: str,
    age_days: int,
):
    source = workspace / f"{name}.csv"
    source.write_text(f"id,value\n1,{value}\n", encoding="utf-8")
    run_id = IngestionRunId.new()
    materializer = FileCsvDatasetVersionMaterializerV2(allowed_roots=(workspace,))
    version = materializer.materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id=_DATASET,
            resource=ResourceReference(
                namespace="gc.test",
                resource_id=name,
                locator=source.resolve().as_uri(),
                media_type="text/csv",
                format="csv",
            ),
            ingestion_run_id=run_id,
            created_at=_NOW - timedelta(days=age_days),
        )
    )
    return store.put(version)


def _intent(reference, expected_revision: PublicationRevision) -> PublicationIntent:
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=expected_revision,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=_NOW,
    )


def _environment(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = FileDatasetVersionStore(root=tmp_path / "store")
    ledger = MemoryPublicationLedger()
    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: _NOW,
    )
    loader = RetentionStateLoader(
        store=store,
        publisher=publisher,
        ledger=ledger,
        holds=ledger,
    )
    return workspace, store, ledger, publisher, loader


def _plan(loader: RetentionStateLoader):
    return RetentionPlanner.plan(
        loader.capture(_DATASET),
        policy=RetentionPolicy(keep_last=1),
        created_at=_NOW + timedelta(minutes=1),
    )


def test_filesystem_gc_protects_current_hold_and_unresolved_then_deletes_candidate(
    tmp_path: Path,
) -> None:
    workspace, store, ledger, publisher, loader = _environment(tmp_path)
    v1 = _put_version(store, workspace, name="v1", value="one", age_days=40)
    v2 = _put_version(store, workspace, name="v2", value="two", age_days=30)
    v3 = _put_version(store, workspace, name="v3", value="three", age_days=20)
    v4 = _put_version(store, workspace, name="v4", value="four", age_days=10)

    published = publisher.compare_and_publish(_intent(v4, PublicationRevision.initial()))
    assert published.snapshot is not None
    ledger.place_hold(
        VersionHold(
            dataset_version=v2,
            held_at=_NOW - timedelta(hours=1),
            reason="audit",
        )
    )
    ledger.register(_intent(v3, published.snapshot.revision))

    plan = _plan(loader)
    assert tuple(reference.identity for reference in plan.candidate_versions) == (v1.identity,)
    assert {reference.identity for reference in plan.protected_versions} == {
        v2.identity,
        v3.identity,
        v4.identity,
    }
    record_retention_plan(ledger, plan)

    collector = FileDatasetVersionGarbageCollector(
        store=store,
        ledger=ledger,
        guard=GarbageCollectionPlanGuard(plan=plan, state_loader=loader),
    )
    deleted = collector.delete(
        v1,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=2),
    )
    assert deleted.status is DatasetVersionDeletionStatus.DELETED

    repeated = collector.delete(
        v1,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=3),
    )
    assert repeated.status is DatasetVersionDeletionStatus.ALREADY_ABSENT


def test_filesystem_stale_plan_cannot_delete_version_that_becomes_current(
    tmp_path: Path,
) -> None:
    workspace, store, ledger, publisher, loader = _environment(tmp_path)
    old = _put_version(store, workspace, name="old", value="old", age_days=30)
    current = _put_version(store, workspace, name="current", value="current", age_days=1)
    first = publisher.compare_and_publish(_intent(current, PublicationRevision.initial()))
    assert first.snapshot is not None
    plan = _plan(loader)
    assert old.identity in {reference.identity for reference in plan.candidate_versions}

    promoted = publisher.compare_and_publish(_intent(old, first.snapshot.revision))
    assert promoted.snapshot is not None
    collector = FileDatasetVersionGarbageCollector(
        store=store,
        ledger=ledger,
        guard=GarbageCollectionPlanGuard(plan=plan, state_loader=loader),
    )
    outcome = collector.delete(
        old,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=2),
    )

    assert outcome.status is DatasetVersionDeletionStatus.FAILED
    assert outcome.failure is not None
    assert outcome.failure.error_code == "governance.gc.stale_plan"
    assert store.get(_DATASET, old.version_id).identity == old.identity


def test_filesystem_gc_rejects_symlink_escape_without_touching_external_path(
    tmp_path: Path,
) -> None:
    workspace, store, ledger, publisher, loader = _environment(tmp_path)
    candidate = _put_version(store, workspace, name="candidate", value="a", age_days=30)
    newest = _put_version(store, workspace, name="newest", value="b", age_days=1)
    publisher.compare_and_publish(_intent(newest, PublicationRevision.initial()))
    plan = _plan(loader)

    target = store._version_dir(candidate.dataset_id, candidate.version_id)
    shutil.rmtree(target)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    target.symlink_to(outside, target_is_directory=True)

    collector = FileDatasetVersionGarbageCollector(
        store=store,
        ledger=ledger,
        guard=GarbageCollectionPlanGuard(plan=plan, state_loader=loader),
    )
    outcome = collector.delete(
        candidate,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=2),
    )

    assert outcome.status is DatasetVersionDeletionStatus.FAILED
    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_filesystem_uncertain_delete_requires_provider_truth_reconciliation(
    tmp_path: Path,
) -> None:
    workspace, store, ledger, publisher, loader = _environment(tmp_path)
    candidate = _put_version(store, workspace, name="candidate", value="a", age_days=30)
    newest = _put_version(store, workspace, name="newest", value="b", age_days=1)
    publisher.compare_and_publish(_intent(newest, PublicationRevision.initial()))
    plan = _plan(loader)

    def inject(phase: str) -> None:
        if phase == "after_delete":
            raise OSError("simulated acknowledgement loss")

    collector = FileDatasetVersionGarbageCollector(
        store=store,
        ledger=ledger,
        guard=GarbageCollectionPlanGuard(plan=plan, state_loader=loader),
        fault_injector=inject,
    )
    outcome = collector.delete(
        candidate,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=2),
    )

    assert outcome.status is DatasetVersionDeletionStatus.UNKNOWN_OUTCOME
    assert outcome.failure is not None
    assert outcome.failure.uncertainty is OutcomeUncertainty.REQUIRES_RECONCILIATION

    reconciled = collector.reconcile_delete(
        candidate,
        plan_id=plan.plan_id,
        reconciled_at=_NOW + timedelta(minutes=3),
    )
    assert (
        reconciled.status
        is DatasetVersionDeletionReconciliationStatus.CONFIRMED_DELETED
    )
