from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.adapters.s3 import (
    S3ArtifactStoreV2,
    S3ConditionalDatasetPublisher,
    S3DatasetVersionStoreV2,
)
from pyingestkit.datasets import build_dataset_version
from pyingestkit.decoders import CsvDecoder, DecodeRequest, DecodeStatus
from pyingestkit.domain.artifacts import ArtifactKind, ArtifactPutStatus, PutArtifactRequest
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

ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")

pytestmark = pytest.mark.skipif(
    not ENDPOINT or not BUCKET,
    reason="S3-compatible endpoint and bucket are required for LOT-28 rollback",
)

_NOW = datetime(2026, 10, 4, 3, 30, tzinfo=UTC)
_DATASET_ID = "governance.s3_rollback"


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


def _environment():
    assert BUCKET is not None
    client = _client()
    _ensure_bucket(client)
    prefix = f"lot28-rollback/{uuid4().hex}"
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
    return store, artifacts, ledger


def _put_version(
    *,
    artifacts: S3ArtifactStoreV2,
    store: S3DatasetVersionStoreV2,
    name: str,
    value: str,
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
                namespace="rollback.test",
                resource_id=name,
                locator=f"https://example.invalid/{name}.csv",
            ),
            source_acquired_at=_NOW,
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
        dataset_id=_DATASET_ID,
        request=request,
        result=decoded,
        created_at=_NOW,
    )
    return store.put(version)


def _intent(reference, revision: PublicationRevision, *, requested_at: datetime):
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=revision,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=requested_at,
    )


def _publisher(store, ledger, when, *, fault_injector=None):
    return S3ConditionalDatasetPublisher(
        store=store,
        ledger=ledger,
        clock=lambda: when,
        fault_injector=fault_injector,
    )


def test_s3_rollback_uses_provider_cas_and_preserves_version_bytes() -> None:
    store, artifacts, ledger = _environment()
    v1 = _put_version(artifacts=artifacts, store=store, name="v1", value="one")
    v2 = _put_version(artifacts=artifacts, store=store, name="v2", value="two")

    publisher = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    first = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert first.snapshot is not None
    current = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision, requested_at=_NOW)
    )
    assert current.snapshot is not None

    immutable_before = store.read(v1)
    intent = _intent(
        v1,
        current.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    service = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=3)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=2),
    )
    outcome = service.rollback(intent)

    assert outcome.status is ConditionalPublicationStatus.SUCCEEDED
    assert outcome.snapshot is not None
    assert outcome.snapshot.published_dataset is not None
    assert outcome.snapshot.published_dataset.version.identity == v1.identity
    assert outcome.snapshot.revision != current.snapshot.revision
    assert store.read(v1) == immutable_before
    assert [event.event_type for event in ledger.list_events(intent.operation_id)] == [
        PublicationLifecycleEventType.ROLLBACK_REQUESTED,
        PublicationLifecycleEventType.ROLLBACK_COMMITTED,
    ]


def test_s3_stale_rollback_conflicts_against_newer_publication() -> None:
    store, artifacts, ledger = _environment()
    v1 = _put_version(artifacts=artifacts, store=store, name="v1", value="one")
    v2 = _put_version(artifacts=artifacts, store=store, name="v2", value="two")
    v3 = _put_version(artifacts=artifacts, store=store, name="v3", value="three")

    publisher = _publisher(store, ledger, _NOW + timedelta(seconds=1))
    first = publisher.compare_and_publish(
        _intent(v1, PublicationRevision.initial(), requested_at=_NOW)
    )
    assert first.snapshot is not None
    second = publisher.compare_and_publish(
        _intent(v2, first.snapshot.revision, requested_at=_NOW)
    )
    assert second.snapshot is not None

    stale = _intent(
        v1,
        second.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    newer = _publisher(
        store,
        ledger,
        _NOW + timedelta(seconds=2),
    ).compare_and_publish(
        _intent(v3, second.snapshot.revision, requested_at=_NOW + timedelta(seconds=2))
    )
    assert newer.snapshot is not None

    service = GovernedRollbackService(
        store=store,
        publisher=_publisher(store, ledger, _NOW + timedelta(seconds=3)),
        ledger=ledger,
        clock=lambda: _NOW + timedelta(seconds=3),
    )
    outcome = service.rollback(stale)

    assert outcome.status is ConditionalPublicationStatus.CONFLICT
    current = publisher.inspect(_DATASET_ID)
    assert current.published_dataset is not None
    assert current.published_dataset.version.identity == v3.identity
    assert [event.event_type for event in ledger.list_events(stale.operation_id)] == [
        PublicationLifecycleEventType.ROLLBACK_REQUESTED,
        PublicationLifecycleEventType.PUBLICATION_CONFLICT,
    ]


def test_s3_unknown_rollback_is_reconciled_without_republication() -> None:
    store, artifacts, ledger = _environment()
    v1 = _put_version(artifacts=artifacts, store=store, name="v1", value="one")
    v2 = _put_version(artifacts=artifacts, store=store, name="v2", value="two")

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
        if phase == "after_conditional_write":
            raise OSError("simulated rollback acknowledgement loss")

    intent = _intent(
        v1,
        current.snapshot.revision,
        requested_at=_NOW + timedelta(seconds=2),
    )
    service = GovernedRollbackService(
        store=store,
        publisher=_publisher(
            store,
            ledger,
            _NOW + timedelta(seconds=3),
            fault_injector=lose_acknowledgement,
        ),
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
