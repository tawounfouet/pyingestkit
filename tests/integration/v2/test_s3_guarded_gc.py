from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.adapters.s3 import (
    S3ArtifactStoreV2,
    S3ConditionalDatasetPublisher,
    S3DatasetVersionGarbageCollector,
    S3DatasetVersionStoreV2,
)
from pyingestkit.datasets import build_dataset_version
from pyingestkit.decoders import CsvDecoder, DecodeRequest, DecodeStatus
from pyingestkit.domain.artifacts import ArtifactKind, ArtifactPutStatus, PutArtifactRequest
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
from pyingestkit.governance.retention import RetentionPlanner, RetentionStateLoader

ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")

pytestmark = pytest.mark.skipif(
    not ENDPOINT or not BUCKET,
    reason="S3-compatible endpoint and bucket are required for LOT-27 guarded GC",
)

_NOW = datetime(2026, 10, 4, 2, 0, tzinfo=UTC)
_DATASET = "governance.s3_gc"


def _client():
    import boto3

    assert ENDPOINT is not None
    return boto3.client("s3", endpoint_url=ENDPOINT, region_name="us-east-1")


def _ensure_bucket(client) -> None:
    assert BUCKET is not None
    try:
        client.create_bucket(Bucket=BUCKET)
    except client.exceptions.BucketAlreadyOwnedByYou:
        pass
    except client.exceptions.BucketAlreadyExists:
        pass


def _put_version(
    *,
    artifacts: S3ArtifactStoreV2,
    versions: S3DatasetVersionStoreV2,
    name: str,
    value: str,
    age_days: int,
):
    run_id = IngestionRunId.new()
    correlation = CorrelationContext(ingestion_run_id=str(run_id))
    content = f"id,value\n1,{value}\n".encode()
    artifact = artifacts.put(
        PutArtifactRequest(
            ingestion_run_id=run_id,
            correlation=correlation,
            kind=ArtifactKind.RAW,
            name=f"{name}.csv",
            content=content,
            media_type="text/csv",
            source_resource=ResourceReference(
                namespace="gc.test",
                resource_id=name,
                locator=f"https://example.invalid/{name}.csv",
            ),
            source_acquired_at=_NOW - timedelta(days=age_days),
        )
    )
    assert artifact.status is ArtifactPutStatus.SUCCEEDED
    assert artifact.reference is not None
    request = DecodeRequest(
        ingestion_run_id=run_id,
        correlation=correlation,
        artifact=artifact.reference,
        content=content,
    )
    decoded = CsvDecoder().decode(request)
    assert decoded.status is DecodeStatus.SUCCEEDED
    version = build_dataset_version(
        dataset_id=_DATASET,
        request=request,
        result=decoded,
        created_at=_NOW - timedelta(days=age_days),
    )
    return versions.put(version)


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


def _environment():
    assert BUCKET is not None
    client = _client()
    _ensure_bucket(client)
    prefix = f"lot27-gc/{uuid4().hex}"
    store = S3DatasetVersionStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        client=client,
    )
    artifacts = S3ArtifactStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        client=client,
    )
    ledger = MemoryPublicationLedger()
    publisher = S3ConditionalDatasetPublisher(
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
    return client, store, artifacts, ledger, publisher, loader


def _plan(loader: RetentionStateLoader):
    return RetentionPlanner.plan(
        loader.capture(_DATASET),
        policy=RetentionPolicy(keep_last=1),
        created_at=_NOW + timedelta(minutes=1),
    )


def test_s3_gc_deletes_only_planned_candidate_and_repeat_is_safe() -> None:
    _, store, artifacts, ledger, publisher, loader = _environment()
    candidate = _put_version(
        artifacts=artifacts,
        versions=store,
        name="candidate",
        value="a",
        age_days=30,
    )
    newest = _put_version(
        artifacts=artifacts,
        versions=store,
        name="newest",
        value="b",
        age_days=1,
    )
    publisher.compare_and_publish(_intent(newest, PublicationRevision.initial()))
    plan = _plan(loader)
    assert tuple(reference.identity for reference in plan.candidate_versions) == (
        candidate.identity,
    )

    collector = S3DatasetVersionGarbageCollector(
        store=store,
        ledger=ledger,
        guard=GarbageCollectionPlanGuard(plan=plan, state_loader=loader),
    )
    deleted = collector.delete(
        candidate,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=2),
    )
    assert deleted.status is DatasetVersionDeletionStatus.DELETED

    repeated = collector.delete(
        candidate,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=3),
    )
    assert repeated.status is DatasetVersionDeletionStatus.ALREADY_ABSENT


def test_s3_stale_plan_cannot_delete_newly_held_version() -> None:
    _, store, artifacts, ledger, publisher, loader = _environment()
    candidate = _put_version(
        artifacts=artifacts,
        versions=store,
        name="candidate",
        value="a",
        age_days=30,
    )
    newest = _put_version(
        artifacts=artifacts,
        versions=store,
        name="newest",
        value="b",
        age_days=1,
    )
    publisher.compare_and_publish(_intent(newest, PublicationRevision.initial()))
    plan = _plan(loader)
    ledger.place_hold(
        VersionHold(
            dataset_version=candidate,
            held_at=_NOW + timedelta(seconds=10),
            reason="investigation",
        )
    )

    collector = S3DatasetVersionGarbageCollector(
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
    assert outcome.failure is not None
    assert outcome.failure.error_code == "governance.gc.stale_plan"
    assert store.get(_DATASET, candidate.version_id).identity == candidate.identity


def test_s3_gc_rejects_caller_supplied_foreign_locator() -> None:
    _, store, artifacts, ledger, publisher, loader = _environment()
    candidate = _put_version(
        artifacts=artifacts,
        versions=store,
        name="candidate",
        value="a",
        age_days=30,
    )
    newest = _put_version(
        artifacts=artifacts,
        versions=store,
        name="newest",
        value="b",
        age_days=1,
    )
    publisher.compare_and_publish(_intent(newest, PublicationRevision.initial()))
    plan = _plan(loader)
    tampered = replace(
        candidate,
        locator=ResourceReference(
            namespace="pyingestkit.dataset_version.s3",
            resource_id="foreign",
            locator="s3://foreign-bucket/foreign-prefix/snapshot.json",
            media_type="application/json",
            format="json",
        ),
    )

    collector = S3DatasetVersionGarbageCollector(
        store=store,
        ledger=ledger,
        guard=GarbageCollectionPlanGuard(plan=plan, state_loader=loader),
    )
    outcome = collector.delete(
        tampered,
        plan_id=plan.plan_id,
        expected_evidence=plan.evidence_fingerprint,
        requested_at=_NOW + timedelta(minutes=2),
    )

    assert outcome.status is DatasetVersionDeletionStatus.FAILED
    assert store.get(_DATASET, candidate.version_id).identity == candidate.identity


def test_s3_uncertain_delete_reconciles_provider_truth_without_redelete() -> None:
    _, store, artifacts, ledger, publisher, loader = _environment()
    candidate = _put_version(
        artifacts=artifacts,
        versions=store,
        name="candidate",
        value="a",
        age_days=30,
    )
    newest = _put_version(
        artifacts=artifacts,
        versions=store,
        name="newest",
        value="b",
        age_days=1,
    )
    publisher.compare_and_publish(_intent(newest, PublicationRevision.initial()))
    plan = _plan(loader)

    def inject(phase: str) -> None:
        if phase == "after_delete":
            raise OSError("simulated acknowledgement loss")

    collector = S3DatasetVersionGarbageCollector(
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
