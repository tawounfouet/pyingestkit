from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from pyingestkit.adapters.filesystem import (
    FileAccessPolicy,
    FileArtifactStore,
    FileDatasetVersionStore,
    FileSourceConnector,
)
from pyingestkit.adapters.http import (
    HttpAccessPolicy,
    HttpRequestV2,
    HttpResponseV2,
    HttpSourceConnector,
)
from pyingestkit.adapters.postgres import PostgresTargetV2
from pyingestkit.adapters.s3 import S3ArtifactStoreV2, S3DatasetVersionStoreV2
from pyingestkit.datasets import build_dataset_version
from pyingestkit.decoders import CsvDecoder, DecodeRequest, DecodeStatus, JsonDecoder
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.artifacts import (
    ArtifactKind,
    ArtifactPutStatus,
    ArtifactReference,
    PutArtifactRequest,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source, SourceKind
from pyingestkit.domain.targets import TargetLoadModeV2
from pyingestkit.ports.artifacts import ArtifactStore
from pyingestkit.ports.dataset_versions import DatasetPublisher, DatasetVersionStore
from pyingestkit.ports.decoders import Decoder
from pyingestkit.ports.sources import SourceConnector, SourceConnectorCapability
from pyingestkit.ports.targets import DatasetTargetV2

ROOT = Path(__file__).resolve().parents[3]
MATRIX = ROOT / "tests" / "fixtures" / "conformance" / "v2" / "provider_port_matrix.json"


class _ClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class _MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        try:
            value = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _ClientError("404") from exc
        return {
            "Metadata": dict(value["Metadata"]),
            "ContentLength": len(value["Body"]),
        }

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        identity = (str(kwargs["Bucket"]), str(kwargs["Key"]))
        if kwargs.get("IfNoneMatch") == "*" and identity in self.objects:
            raise _ClientError("PreconditionFailed")
        self.objects[identity] = {
            "Body": bytes(kwargs["Body"]),
            "Metadata": dict(kwargs.get("Metadata", {})),
            "ContentType": kwargs.get("ContentType"),
        }
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        try:
            value = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise _ClientError("NoSuchKey") from exc
        return {
            "Body": BytesIO(bytes(value["Body"])),
            "Metadata": dict(value["Metadata"]),
        }

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
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


class _StaticHttpClient:
    def send(self, request: HttpRequestV2) -> HttpResponseV2:
        return HttpResponseV2(
            status_code=200,
            url=request.url,
            headers=(("Content-Type", "text/csv"),),
            content=b"id,name\n1,Ada\n",
        )


def _correlation() -> tuple[IngestionRunId, CorrelationContext]:
    run_id = IngestionRunId.new()
    return run_id, CorrelationContext(ingestion_run_id=str(run_id))


def _artifact_request() -> PutArtifactRequest:
    run_id, correlation = _correlation()
    return PutArtifactRequest(
        ingestion_run_id=run_id,
        correlation=correlation,
        kind=ArtifactKind.REPORT,
        name="report.json",
        content=b'{"ok":true}',
        media_type="application/json",
    )


def _decode_request(content: bytes, media_type: str) -> DecodeRequest:
    run_id, correlation = _correlation()
    checksum = hashlib.sha256(content).hexdigest()
    artifact = ArtifactReference(
        artifact_id="conformance-raw",
        kind="raw",
        resource=ResourceReference(
            namespace="pyingestkit.conformance",
            resource_id="conformance-raw",
            locator="file:///tmp/conformance-raw",
            media_type=media_type,
        ),
        checksum=checksum,
        checksum_algorithm="sha256",
        media_type=media_type,
        size_bytes=len(content),
        created_at=datetime(2026, 10, 3, 12, 0, tzinfo=UTC),
    )
    return DecodeRequest(
        ingestion_run_id=run_id,
        correlation=correlation,
        artifact=artifact,
        content=content,
    )


def _dataset_version():
    request = _decode_request(b"id,name\n1,Ada\n", "text/csv")
    result = CsvDecoder().decode(request)
    assert result.status is DecodeStatus.SUCCEEDED
    return build_dataset_version(
        dataset_id="conformance.people",
        request=request,
        result=result,
        created_at=datetime(2026, 10, 3, 12, 5, tzinfo=UTC),
    )


def test_source_connector_provider_matrix(tmp_path: Path) -> None:
    source_file = tmp_path / "source.csv"
    source_file.write_bytes(b"id,name\n1,Ada\n")
    file_connector = FileSourceConnector(
        policy=FileAccessPolicy(allowed_roots=(tmp_path,))
    )
    http_connector = HttpSourceConnector(
        policy=HttpAccessPolicy(
            allowed_hosts=("api.example.test",),
            retry_backoff_seconds=0.0,
        ),
        client=_StaticHttpClient(),
    )

    for connector, source, expected_id, expected_kind in (
        (
            file_connector,
            Source.file(path=str(source_file)),
            "pyingestkit.file",
            SourceKind.FILE,
        ),
        (
            http_connector,
            Source.http(url="https://api.example.test/data.csv"),
            "pyingestkit.http",
            SourceKind.HTTP,
        ),
    ):
        assert isinstance(connector, SourceConnector)
        assert connector.descriptor.id == expected_id
        assert connector.descriptor.supported_source_kinds == (expected_kind,)
        assert SourceConnectorCapability.ACQUIRE in connector.descriptor.capabilities
        run_id, correlation = _correlation()
        request = AcquisitionRequest(
            source=source,
            ingestion_run_id=run_id,
            correlation=correlation,
        )
        result = connector.acquire(request)
        assert result.status is AcquisitionStatus.SUCCEEDED
        assert result.ingestion_run_id == run_id
        assert result.correlation == correlation
        assert result.source_kind is expected_kind
        assert result.content == b"id,name\n1,Ada\n"
        assert result.failure is None


def test_artifact_store_provider_matrix(tmp_path: Path) -> None:
    stores = (
        FileArtifactStore(root=tmp_path / "artifacts"),
        S3ArtifactStoreV2(
            bucket="conformance",
            prefix="lot19",
            client=_MemoryS3(),
        ),
    )

    for store in stores:
        assert isinstance(store, ArtifactStore)
        request = _artifact_request()
        first = store.put(request)
        second = store.put(request)
        assert first.status is ArtifactPutStatus.SUCCEEDED
        assert first.reference is not None
        assert store.exists(first.reference) is True
        assert store.open(first.reference).read() == request.content
        assert second.status is ArtifactPutStatus.CONFLICT


def test_dataset_version_store_and_publisher_matrix(tmp_path: Path) -> None:
    stores = (
        FileDatasetVersionStore(root=tmp_path / "versions"),
        S3DatasetVersionStoreV2(
            bucket="conformance",
            prefix="lot19",
            client=_MemoryS3(),
        ),
    )

    for store in stores:
        assert isinstance(store, DatasetVersionStore)
        assert isinstance(store, DatasetPublisher)
        version = _dataset_version()
        first_reference = store.put(version)
        second_reference = store.put(version)
        assert second_reference == first_reference
        assert store.read(first_reference) == version.representation
        assert store.list(version.dataset_id) == (first_reference,)

        published = store.publish(
            first_reference,
            ingestion_run_id=version.ingestion_run_id,
            published_at=datetime(2026, 10, 3, 12, 10, tzinfo=UTC),
        )
        republished = store.publish(
            first_reference,
            ingestion_run_id=IngestionRunId.new(),
            published_at=datetime(2026, 10, 3, 12, 15, tzinfo=UTC),
        )
        assert store.get_published(version.dataset_id) == published
        assert republished == published


def test_decoder_provider_matrix() -> None:
    cases = (
        (CsvDecoder(), b"id,name\n1,Ada\n", "text/csv", "csv"),
        (JsonDecoder(), b'[{"id":"1","name":"Ada"}]', "application/json", "json"),
    )

    for decoder, content, media_type, expected_id in cases:
        assert isinstance(decoder, Decoder)
        assert decoder.descriptor.id == expected_id
        result = decoder.decode(_decode_request(content, media_type))
        assert result.status is DecodeStatus.SUCCEEDED
        assert result.failure is None
        assert result.row_count == 1


def test_postgres_target_port_and_capability_contract_without_connection() -> None:
    target = PostgresTargetV2(
        target_id="postgres.conformance",
        dsn="postgresql://user:secret@localhost/conformance",
    )

    assert isinstance(target, DatasetTargetV2)
    assert target.descriptor.id == "pyingestkit.postgres"
    assert target.descriptor.transactional is True
    assert target.descriptor.bulk_load is True
    assert set(target.descriptor.supported_modes) == {
        mode.value for mode in TargetLoadModeV2
    }
    assert "secret" not in target.safe_dsn
    target.close()
    target.close()
    assert target.closed is True


def test_provider_port_manifest_matches_executable_matrix() -> None:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert payload["schema"] == "pyingestkit.v2-provider-port-conformance"
    assert payload["schema_version"] == "1"
    assert payload["lot"] == "LOT-19"

    expected = {
        "pyingestkit.file": ("SourceConnector",),
        "pyingestkit.http": ("SourceConnector",),
        "pyingestkit.artifact.file": ("ArtifactStore",),
        "pyingestkit.artifact.s3": ("ArtifactStore",),
        "pyingestkit.dataset-version.file": (
            "DatasetVersionStore",
            "DatasetPublisher",
        ),
        "pyingestkit.dataset-version.s3": (
            "DatasetVersionStore",
            "DatasetPublisher",
        ),
        "pyingestkit.postgres": ("DatasetTargetV2",),
        "csv": ("Decoder",),
        "json": ("Decoder",),
    }
    providers = payload["providers"]
    assert isinstance(providers, list)
    assert {item["provider_id"] for item in providers} == set(expected)

    for item in providers:
        provider_id = item["provider_id"]
        assert tuple(item["ports"]) == expected[provider_id]
        assert item["qualification"] in {"offline", "offline+service"}
        evidence = item["conformance_evidence"] + item["service_evidence"]
        assert evidence
        for relative in evidence:
            assert (ROOT / relative).is_file(), f"Missing LOT-19 evidence: {relative}"
