from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

import pytest

from pyingestkit.adapters.s3 import S3ArtifactStoreV2, S3DatasetVersionStoreV2
from pyingestkit.domain.artifacts import ArtifactIntegrityError, ArtifactKind, PutArtifactRequest
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId

from .test_dataset_version import _version


class _ClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class _MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, object]] = {}

    def head_object(self, *, Bucket: str, Key: str):
        try:
            value = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _ClientError("404") from exc
        return {
            "Metadata": dict(value["Metadata"]),
            "ContentLength": len(value["Body"]),
        }

    def put_object(self, **kwargs):
        bucket = str(kwargs["Bucket"])
        key = str(kwargs["Key"])
        identity = (bucket, key)
        if kwargs.get("IfNoneMatch") == "*" and identity in self.objects:
            raise _ClientError("PreconditionFailed")
        self.objects[identity] = {
            "Body": bytes(kwargs["Body"]),
            "Metadata": dict(kwargs.get("Metadata", {})),
            "ContentType": kwargs.get("ContentType"),
        }
        return {}

    def get_object(self, *, Bucket: str, Key: str):
        try:
            value = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _ClientError("NoSuchKey") from exc
        return {
            "Body": BytesIO(bytes(value["Body"])),
            "Metadata": dict(value["Metadata"]),
        }

    def list_objects_v2(self, **kwargs):
        bucket = str(kwargs["Bucket"])
        prefix = str(kwargs["Prefix"])
        keys = sorted(
            key
            for object_bucket, key in self.objects
            if object_bucket == bucket and key.startswith(prefix)
        )
        return {
            "Contents": [{"Key": key} for key in keys],
            "IsTruncated": False,
        }


def _raw_request(content: bytes = b"id,name\n1,Ada\n") -> PutArtifactRequest:
    run_id = IngestionRunId.new()
    correlation = CorrelationContext(ingestion_run_id=str(run_id))
    return PutArtifactRequest(
        ingestion_run_id=run_id,
        correlation=correlation,
        kind=ArtifactKind.RAW,
        name="source.raw",
        content=content,
        source_resource=ResourceReference(
            namespace="test.source",
            resource_id="source-1",
            locator="https://example.test/data.csv",
        ),
        source_acquired_at=datetime(2026, 10, 3, 11, 0, tzinfo=UTC),
    )


def test_s3_artifact_store_round_trips_and_is_create_once() -> None:
    client = _MemoryS3()
    store = S3ArtifactStoreV2(bucket="demo", prefix="tenant/v2", client=client)
    request = _raw_request()

    first = store.put(request)
    second = store.put(request)

    assert first.reference is not None
    assert first.raw_evidence is not None
    assert store.open(first.reference).read() == request.content
    assert store.exists(first.reference) is True
    assert second.status.value == "conflict"


def test_s3_artifact_reader_detects_tampering() -> None:
    client = _MemoryS3()
    store = S3ArtifactStoreV2(bucket="demo", client=client)
    result = store.put(_raw_request())
    assert result.reference is not None
    key = result.reference.resource.locator
    assert key is not None
    object_key = key.split("demo/", 1)[1]
    client.objects[("demo", object_key)]["Body"] = b"tampered"

    with pytest.raises(ArtifactIntegrityError):
        store.open(result.reference).read()


def test_s3_dataset_version_store_round_trip_and_publication() -> None:
    client = _MemoryS3()
    first_store = S3DatasetVersionStoreV2(bucket="demo", prefix="tenant/v2", client=client)
    version = _version(b"id,name\n1,Ada\n")

    reference = first_store.put(version)
    published = first_store.publish(
        reference,
        ingestion_run_id=version.ingestion_run_id,
        published_at=datetime(2026, 10, 3, 11, 5, tzinfo=UTC),
    )

    second_store = S3DatasetVersionStoreV2(bucket="demo", prefix="tenant/v2", client=client)
    assert second_store.get(reference.dataset_id, reference.version_id) == reference
    assert second_store.read(reference) == version.representation
    assert second_store.list(reference.dataset_id) == (reference,)
    assert second_store.get_published(reference.dataset_id) == published


def test_s3_dataset_version_store_rejects_tampered_snapshot() -> None:
    client = _MemoryS3()
    store = S3DatasetVersionStoreV2(bucket="demo", client=client)
    version = _version(b"id,name\n1,Ada\n")
    reference = store.put(version)
    assert reference.locator is not None
    assert reference.locator.locator is not None
    object_key = reference.locator.locator.split("demo/", 1)[1]
    client.objects[("demo", object_key)]["Body"] = b"{}"

    with pytest.raises(ValueError, match="SHA-256"):
        store.read(reference)
