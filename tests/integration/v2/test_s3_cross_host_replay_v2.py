from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pyingestkit.adapters.s3 import S3ArtifactStoreV2, S3DatasetVersionStoreV2
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.datasets import build_dataset_version
from pyingestkit.decoders import CsvDecoder, DecodeRequest, DecodeStatus
from pyingestkit.domain.artifacts import ArtifactKind, ArtifactPutStatus, PutArtifactRequest
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source
from pyingestkit.replay.v2 import ReplayRequest, ReplayServiceV2
from pyingestkit.runtime.v2 import IngestionRuntime
from pyingestkit.validation.v2 import RequiredFieldV2

ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")

pytestmark = pytest.mark.skipif(
    not ENDPOINT or not BUCKET,
    reason="S3-compatible endpoint and bucket are required for V2 cross-host replay",
)

_NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def test_v2_s3_cross_host_strict_replay_without_workspace_or_live_source() -> None:
    import boto3

    assert ENDPOINT is not None
    assert BUCKET is not None
    client = boto3.client("s3", endpoint_url=ENDPOINT, region_name="us-east-1")
    try:
        client.create_bucket(Bucket=BUCKET)
    except client.exceptions.BucketAlreadyOwnedByYou:
        pass

    prefix = f"v2-cross-host/{uuid4().hex}"
    content = b"id,name\n1,Ada\n"
    definition = IngestionDefinition(
        name="demo.cross_host_v2",
        source=Source.file(path="/source-is-intentionally-unavailable.csv"),
        decoder="csv",
        dataset="demo.cross_host_v2",
    )

    source_run_id = IngestionRunId.new()
    source_context = CorrelationContext(ingestion_run_id=str(source_run_id))
    host_a_artifacts = S3ArtifactStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
    )
    host_a_versions = S3DatasetVersionStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
    )

    raw_put = host_a_artifacts.put(
        PutArtifactRequest(
            ingestion_run_id=source_run_id,
            correlation=source_context,
            kind=ArtifactKind.RAW,
            name="source.raw",
            content=content,
            media_type="text/csv",
            source_resource=ResourceReference(
                namespace="test.source",
                resource_id="gone-source",
                locator="file:///source-is-intentionally-unavailable.csv",
            ),
            source_acquired_at=_NOW,
        )
    )
    assert raw_put.status is ArtifactPutStatus.SUCCEEDED
    assert raw_put.reference is not None
    origin_raw = raw_put.reference

    decode_request = DecodeRequest(
        ingestion_run_id=source_run_id,
        correlation=source_context,
        artifact=origin_raw,
        content=content,
    )
    decoded = CsvDecoder().decode(decode_request)
    assert decoded.status is DecodeStatus.SUCCEEDED
    version = build_dataset_version(
        dataset_id=definition.dataset,
        request=decode_request,
        result=decoded,
        created_at=_NOW,
    )
    expected = host_a_versions.put(version)
    published = host_a_versions.publish(
        expected,
        ingestion_run_id=source_run_id,
        published_at=_NOW,
    )

    del host_a_artifacts
    del host_a_versions

    host_b_artifacts = S3ArtifactStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
    )
    host_b_versions = S3DatasetVersionStoreV2(
        bucket=BUCKET,
        prefix=prefix,
        endpoint_url=ENDPOINT,
        region_name="us-east-1",
    )
    decoders = DecoderRegistry()
    decoders.register(CsvDecoder())
    runtime = IngestionRuntime(
        sources=SourceRegistry(),
        decoders=decoders,
        artifacts=host_b_artifacts,
        versions=host_b_versions,
        publisher=host_b_versions,
        clock=lambda: _NOW,
    )
    replay = ReplayServiceV2(runtime=runtime, clock=lambda: _NOW).replay(
        ReplayRequest(
            source_run_id=source_run_id,
            definition=definition,
            origin_raw_artifact=origin_raw,
            expected_dataset_version=expected,
        ),
        validation_rules=(RequiredFieldV2("id"),),
    )

    assert replay.succeeded is True
    assert replay.matched is True
    assert replay.replay_run_id != source_run_id
    assert replay.replay_raw_artifact.checksum == origin_raw.checksum
    assert replay.replay_raw_artifact.resource.locator != origin_raw.resource.locator
    assert replay.ingestion.dataset_version == expected
    assert replay.ingestion.published_dataset is None
    assert host_b_versions.read(expected) == version.representation
    assert host_b_versions.get_published(definition.dataset) == published
