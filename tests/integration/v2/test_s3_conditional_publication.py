from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
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
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, OutcomeUncertainty
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance import (
    ConditionalPublicationStatus,
    PublicationIntent,
    PublicationOperationId,
    PublicationRevision,
)

ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")

pytestmark = pytest.mark.skipif(
    not ENDPOINT or not BUCKET,
    reason="S3-compatible endpoint and bucket are required for LOT-26 conditional publication",
)

_NOW = datetime(2026, 10, 4, 0, 0, tzinfo=UTC)
_DATASET_ID = "governance.s3_cross_host"


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
):
    run_id = IngestionRunId.new()
    correlation = CorrelationContext(ingestion_run_id=str(run_id))
    content = f"id,value\n1,{value}\n".encode()
    stored_artifact = artifacts.put(
        PutArtifactRequest(
            ingestion_run_id=run_id,
            correlation=correlation,
            kind=ArtifactKind.RAW,
            name=f"{name}.csv",
            content=content,
            media_type="text/csv",
            source_resource=ResourceReference(
                namespace="test.source",
                resource_id=name,
                locator=f"https://example.invalid/{name}.csv",
            ),
            source_acquired_at=_NOW,
        )
    )
    assert stored_artifact.status is ArtifactPutStatus.SUCCEEDED
    assert stored_artifact.reference is not None
    decode_request = DecodeRequest(
        ingestion_run_id=run_id,
        correlation=correlation,
        artifact=stored_artifact.reference,
        content=content,
    )
    decoded = CsvDecoder().decode(decode_request)
    assert decoded.status is DecodeStatus.SUCCEEDED
    version = build_dataset_version(
        dataset_id=_DATASET_ID,
        request=decode_request,
        result=decoded,
        created_at=_NOW,
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


def _race_publishers(
    first: S3ConditionalDatasetPublisher,
    first_intent: PublicationIntent,
    second: S3ConditionalDatasetPublisher,
    second_intent: PublicationIntent,
):
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(first.compare_and_publish, first_intent),
            executor.submit(second.compare_and_publish, second_intent),
        )
        return tuple(future.result(timeout=20) for future in futures)


def _publishers_for_race(
    *,
    store_a: S3DatasetVersionStoreV2,
    store_b: S3DatasetVersionStoreV2,
) -> tuple[S3ConditionalDatasetPublisher, S3ConditionalDatasetPublisher]:
    barrier = threading.Barrier(2)

    def synchronize(phase: str) -> None:
        if phase == "before_conditional_write":
            barrier.wait(timeout=10)

    return (
        S3ConditionalDatasetPublisher(
            store=store_a,
            ledger=MemoryPublicationLedger(),
            clock=lambda: _NOW,
            fault_injector=synchronize,
        ),
        S3ConditionalDatasetPublisher(
            store=store_b,
            ledger=MemoryPublicationLedger(),
            clock=lambda: _NOW,
            fault_injector=synchronize,
        ),
    )


def _stores():
    assert BUCKET is not None
    prefix = f"lot26-s3-cas/{uuid4().hex}"
    client_a = _client()
    client_b = _client()
    _ensure_bucket(client_a)
    store_a = S3DatasetVersionStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        client=client_a,
    )
    store_b = S3DatasetVersionStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        client=client_b,
    )
    artifacts = S3ArtifactStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        client=client_a,
    )
    return client_a, client_b, store_a, store_b, artifacts


def test_lot26_initial_cross_client_race_has_exactly_one_provider_winner() -> None:
    _, _, store_a, store_b, artifacts = _stores()
    first_version = _put_version(
        artifacts=artifacts,
        versions=store_a,
        name="initial-a",
        value="a",
    )
    second_version = _put_version(
        artifacts=artifacts,
        versions=store_a,
        name="initial-b",
        value="b",
    )
    publisher_a, publisher_b = _publishers_for_race(store_a=store_a, store_b=store_b)

    outcomes = _race_publishers(
        publisher_a,
        _intent(first_version, PublicationRevision.initial()),
        publisher_b,
        _intent(second_version, PublicationRevision.initial()),
    )

    assert sorted(outcome.status.value for outcome in outcomes) == ["conflict", "succeeded"]
    loser = next(outcome for outcome in outcomes if outcome.status is ConditionalPublicationStatus.CONFLICT)
    assert loser.failure is not None
    assert loser.failure.error_code == "governance.s3.provider_precondition_conflict"


def test_lot26_existing_revision_cross_client_race_has_exactly_one_provider_winner() -> None:
    _, _, store_a, store_b, artifacts = _stores()
    baseline = _put_version(
        artifacts=artifacts,
        versions=store_a,
        name="baseline",
        value="zero",
    )
    first_version = _put_version(
        artifacts=artifacts,
        versions=store_a,
        name="replace-a",
        value="a",
    )
    second_version = _put_version(
        artifacts=artifacts,
        versions=store_a,
        name="replace-b",
        value="b",
    )
    baseline_publisher = S3ConditionalDatasetPublisher(
        store=store_a,
        ledger=MemoryPublicationLedger(),
        clock=lambda: _NOW,
    )
    committed = baseline_publisher.compare_and_publish(
        _intent(baseline, PublicationRevision.initial())
    )
    assert committed.snapshot is not None

    publisher_a, publisher_b = _publishers_for_race(store_a=store_a, store_b=store_b)
    outcomes = _race_publishers(
        publisher_a,
        _intent(first_version, committed.snapshot.revision),
        publisher_b,
        _intent(second_version, committed.snapshot.revision),
    )

    assert sorted(outcome.status.value for outcome in outcomes) == ["conflict", "succeeded"]
    loser = next(outcome for outcome in outcomes if outcome.status is ConditionalPublicationStatus.CONFLICT)
    assert loser.failure is not None
    assert loser.failure.error_code == "governance.s3.provider_precondition_conflict"


def test_lot26_acknowledgement_loss_is_unknown_then_reconciled_without_republish() -> None:
    client, _, store_a, _, artifacts = _stores()
    reference = _put_version(
        artifacts=artifacts,
        versions=store_a,
        name="unknown",
        value="a",
    )
    ledger = MemoryPublicationLedger()

    def lose_acknowledgement(phase: str) -> None:
        if phase == "after_conditional_write":
            raise OSError("simulated lost acknowledgement")

    publisher = S3ConditionalDatasetPublisher(
        store=store_a,
        ledger=ledger,
        clock=lambda: _NOW,
        fault_injector=lose_acknowledgement,
    )
    intent = _intent(reference, PublicationRevision.initial())
    outcome = publisher.compare_and_publish(intent)

    assert outcome.status is ConditionalPublicationStatus.UNKNOWN_OUTCOME
    assert outcome.failure is not None
    assert outcome.failure.uncertainty is OutcomeUncertainty.REQUIRES_RECONCILIATION
    assert ledger.list_unresolved(_DATASET_ID) == (intent,)

    reconciler = S3ConditionalDatasetPublisher(
        store=store_a,
        ledger=ledger,
        clock=lambda: _NOW,
    )
    reconciled = reconciler.reconcile(intent)
    assert reconciled.status is ConditionalPublicationStatus.SUCCEEDED
    assert reconciled.snapshot is not None
    assert ledger.list_unresolved(_DATASET_ID) == ()

    assert BUCKET is not None
    pointer_key = store_a._published_key(_DATASET_ID)
    response = client.get_object(Bucket=BUCKET, Key=pointer_key)
    body = response["Body"].read()
    payload = json.loads(body)
    assert "etag" not in {str(key).lower() for key in payload}
    assert str(reconciled.snapshot.revision) != str(response["ETag"])
    frozen = store_a.get_published(_DATASET_ID)
    assert frozen is not None
    assert frozen.version.identity == reference.identity
