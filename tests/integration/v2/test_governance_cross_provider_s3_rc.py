from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyingestkit.adapters.postgres import PostgresPublicationLedger
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
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
    RetentionPolicy,
    VersionHold,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance.retention import RetentionPlanner, RetentionStateLoader
from pyingestkit.governance.rollback import GovernedRollbackService

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")
ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")

pytestmark = pytest.mark.skipif(
    not POSTGRES_DSN or not ENDPOINT or not BUCKET,
    reason="PostgreSQL + S3-compatible endpoint are required for LOT-29 cross-provider RC evidence",
)

_NOW = datetime(2026, 10, 4, 5, 30, tzinfo=UTC)


class _CrashOnTerminalLedger:
    """Persist request evidence, then simulate process death before terminal ledger append."""

    def __init__(self, delegate: PostgresPublicationLedger) -> None:
        self._delegate = delegate

    def register(self, intent: PublicationIntent) -> PublicationIntent:
        return self._delegate.register(intent)

    def append(self, event: PublicationLifecycleEvent) -> None:
        if event.event_type in {
            PublicationLifecycleEventType.PUBLICATION_COMMITTED,
            PublicationLifecycleEventType.PUBLICATION_RECONCILED_COMMITTED,
            PublicationLifecycleEventType.ROLLBACK_COMMITTED,
        }:
            raise SystemExit("simulated process crash after provider commit")
        self._delegate.append(event)

    def get_operation(self, operation_id: PublicationOperationId) -> PublicationIntent | None:
        return self._delegate.get_operation(operation_id)

    def list_operations(self, dataset_id: str) -> tuple[PublicationIntent, ...]:
        return self._delegate.list_operations(dataset_id)

    def list_unresolved(self, dataset_id: str | None = None) -> tuple[PublicationIntent, ...]:
        return self._delegate.list_unresolved(dataset_id)

    def list_events(
        self,
        operation_id: PublicationOperationId | None = None,
        *,
        dataset_id: str | None = None,
    ) -> tuple[PublicationLifecycleEvent, ...]:
        return self._delegate.list_events(operation_id, dataset_id=dataset_id)


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
    prefix = f"lot29-cross-provider/{uuid4().hex}"
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
    return store, artifacts


def _put_version(
    *,
    artifacts: S3ArtifactStoreV2,
    store: S3DatasetVersionStoreV2,
    dataset_id: str,
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
                namespace="governance.rc.s3",
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
        dataset_id=dataset_id,
        request=request,
        result=decoded,
        created_at=_NOW - timedelta(days=age_days),
    )
    return store.put(version)


def _intent(reference, revision: PublicationRevision, when: datetime) -> PublicationIntent:
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=revision,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=when,
    )


def _requested_event(intent: PublicationIntent) -> PublicationLifecycleEvent:
    return PublicationLifecycleEvent(
        event_id=f"{intent.operation_id}:publication_requested",
        event_type=PublicationLifecycleEventType.PUBLICATION_REQUESTED,
        dataset_id=intent.dataset_id,
        occurred_at=intent.requested_at,
        operation_id=intent.operation_id,
        dataset_version=intent.dataset_version,
        previous_revision=intent.expected_revision,
    )


def test_s3_postgres_restart_reconciles_crash_before_provider_side_effect() -> None:
    assert POSTGRES_DSN is not None
    dataset_id = f"governance.rc.s3.before.{uuid4().hex}"
    store, artifacts = _environment()
    target = _put_version(
        artifacts=artifacts,
        store=store,
        dataset_id=dataset_id,
        name="target",
        value="before",
        age_days=3,
    )
    intent = _intent(target, PublicationRevision.initial(), _NOW)

    first = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        with first.transaction() as transaction:
            transaction.register(intent)
            transaction.append(_requested_event(intent))
    finally:
        first.close()

    restarted = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        assert restarted.list_unresolved(dataset_id) == (intent,)
        publisher = S3ConditionalDatasetPublisher(
            store=store,
            ledger=restarted,
            clock=lambda: _NOW + timedelta(seconds=1),
        )
        reconciled = publisher.reconcile(intent)

        assert reconciled.status is ConditionalPublicationStatus.FAILED
        assert reconciled.snapshot is not None
        assert reconciled.snapshot.revision == PublicationRevision.initial()
        assert publisher.inspect(dataset_id).published_dataset is None
        assert restarted.list_unresolved(dataset_id) == ()
        assert [event.event_type for event in restarted.list_events(intent.operation_id)] == [
            PublicationLifecycleEventType.PUBLICATION_REQUESTED,
            PublicationLifecycleEventType.PUBLICATION_RECONCILED_NOT_COMMITTED,
        ]
    finally:
        restarted.close()


def test_s3_postgres_crash_after_provider_commit_recovers_then_retains_and_rolls_back() -> None:
    assert POSTGRES_DSN is not None
    dataset_id = f"governance.rc.s3.after.{uuid4().hex}"
    store, artifacts = _environment()
    v0 = _put_version(
        artifacts=artifacts,
        store=store,
        dataset_id=dataset_id,
        name="v0",
        value="zero",
        age_days=30,
    )
    v1 = _put_version(
        artifacts=artifacts,
        store=store,
        dataset_id=dataset_id,
        name="v1",
        value="one",
        age_days=20,
    )
    v2 = _put_version(
        artifacts=artifacts,
        store=store,
        dataset_id=dataset_id,
        name="v2",
        value="two",
        age_days=1,
    )
    publish_intent = _intent(v2, PublicationRevision.initial(), _NOW)

    durable = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        crashing = S3ConditionalDatasetPublisher(
            store=store,
            ledger=_CrashOnTerminalLedger(durable),
            clock=lambda: _NOW + timedelta(seconds=1),
        )
        with pytest.raises(SystemExit, match="process crash"):
            crashing.compare_and_publish(publish_intent)

        provider_truth = crashing.inspect(dataset_id)
        assert provider_truth.published_dataset is not None
        assert provider_truth.published_dataset.version.identity == v2.identity
        assert durable.list_unresolved(dataset_id) == (publish_intent,)
    finally:
        durable.close()

    restarted = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        publisher = S3ConditionalDatasetPublisher(
            store=store,
            ledger=restarted,
            clock=lambda: _NOW + timedelta(seconds=2),
        )
        reconciled = publisher.reconcile(publish_intent)
        assert reconciled.status is ConditionalPublicationStatus.SUCCEEDED
        assert reconciled.snapshot is not None
        assert restarted.list_unresolved(dataset_id) == ()

        hold = VersionHold(
            dataset_version=v0,
            held_at=_NOW + timedelta(seconds=3),
            reason="lot29-cross-provider-proof",
        )
        restarted.place_hold(hold)
        loader = RetentionStateLoader(
            store=store,
            publisher=publisher,
            ledger=restarted,
            holds=restarted,
        )
        state = loader.capture(dataset_id)
        plan = RetentionPlanner.plan(
            state,
            policy=RetentionPolicy(keep_last=1),
            created_at=_NOW + timedelta(minutes=1),
        )
        assert tuple(item.identity for item in plan.candidate_versions) == (v1.identity,)
        assert v0.identity in {item.identity for item in plan.protected_versions}
        assert v2.identity in {item.identity for item in plan.protected_versions}

        restarted.release_hold(v0, released_at=_NOW + timedelta(minutes=2))
        current = publisher.inspect(dataset_id)
        rollback_intent = _intent(
            v0,
            current.revision,
            _NOW + timedelta(minutes=3),
        )
        rollback = GovernedRollbackService(
            store=store,
            publisher=S3ConditionalDatasetPublisher(
                store=store,
                ledger=restarted,
                clock=lambda: _NOW + timedelta(minutes=4),
            ),
            ledger=restarted,
            clock=lambda: _NOW + timedelta(minutes=3),
        ).rollback(rollback_intent)

        assert rollback.status is ConditionalPublicationStatus.SUCCEEDED
        assert rollback.snapshot is not None
        assert rollback.snapshot.published_dataset is not None
        assert rollback.snapshot.published_dataset.version.identity == v0.identity
        assert [
            event.event_type for event in restarted.list_events(rollback_intent.operation_id)
        ] == [
            PublicationLifecycleEventType.ROLLBACK_REQUESTED,
            PublicationLifecycleEventType.ROLLBACK_COMMITTED,
        ]
    finally:
        restarted.close()
