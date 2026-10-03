from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx

from pyingestkit.adapters.filesystem import FileArtifactStore, FileDatasetVersionStore
from pyingestkit.adapters.http import (
    HttpAccessPolicy,
    HttpCredentialResolverV2,
    HttpSourceConnector,
)
from pyingestkit.adapters.http._httpx import HttpxHttpClientV2
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.decoders import CsvDecoder
from pyingestkit.domain.artifacts import (
    ArtifactReference,
    PutArtifactRequest,
    PutArtifactResult,
)
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.resources import CredentialReference
from pyingestkit.domain.sources import Source
from pyingestkit.ports.artifacts import ArtifactReader
from pyingestkit.runtime.v2 import IngestionRuntime
from pyingestkit.validation.v2 import RequiredFieldV2


class _CapturingArtifactStore:
    def __init__(self, delegate: FileArtifactStore) -> None:
        self.delegate = delegate
        self.requests: list[PutArtifactRequest] = []

    def put(self, request: PutArtifactRequest) -> PutArtifactResult:
        self.requests.append(request)
        return self.delegate.put(request)

    def open(self, reference: ArtifactReference) -> ArtifactReader:
        return self.delegate.open(reference)

    def exists(self, reference: ArtifactReference) -> bool:
        return self.delegate.exists(reference)


def test_httpx_runtime_acquires_safe_provenance_before_decode_and_version(
    tmp_path: Path,
) -> None:
    wire_secret = "bearer-runtime-secret"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == f"Bearer {wire_secret}"
        assert request.url.params["page"] == "2"
        return httpx.Response(
            200,
            headers={
                "Content-Type": "text/csv; charset=utf-8",
                "ETag": '"customers-v1"',
                "Last-Modified": "Wed, 02 Sep 2026 10:00:00 GMT",
                "Set-Cookie": "session=response-secret",
            },
            content=b"id,name\n1,Ada\n",
            request=request,
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as native_client:
        connector = HttpSourceConnector(
            policy=HttpAccessPolicy(
                allowed_hosts=("api.example.test",),
                retry_backoff_seconds=0.0,
            ),
            client=HttpxHttpClientV2(client=native_client),
            credential_resolver=HttpCredentialResolverV2(
                lambda credential: {
                    "Authorization": f"Bearer {wire_secret}"
                    if credential.credential_id == "customers-api"
                    else "invalid"
                }
            ),
        )

        sources = SourceRegistry()
        sources.register(connector)
        decoders = DecoderRegistry()
        decoders.register(CsvDecoder())
        artifact_delegate = FileArtifactStore(root=tmp_path / "artifact-store")
        artifacts = _CapturingArtifactStore(artifact_delegate)
        versions = FileDatasetVersionStore(root=tmp_path / "dataset-store")
        runtime = IngestionRuntime(
            sources=sources,
            decoders=decoders,
            artifacts=artifacts,
            versions=versions,
            clock=lambda: datetime(2026, 10, 3, 10, 30, tzinfo=UTC),
        )
        definition = IngestionDefinition(
            name="demo.http_customers",
            source=Source.http(
                url="https://api.example.test/customers.csv?page=2",
                credential=CredentialReference("customers-api", provider="test"),
            ),
            decoder="csv",
            dataset="demo.http_customers",
        )

        result = runtime.execute(
            definition,
            validation_rules=(RequiredFieldV2("id"),),
        )

    assert result.succeeded is True
    assert result.dataset_version is not None
    assert result.published_dataset is None
    assert len(versions.read(result.dataset_version)) == 1

    assert len(artifacts.requests) == 1
    raw_request = artifacts.requests[0]
    assert raw_request.content == b"id,name\n1,Ada\n"
    assert raw_request.source_resource is not None
    source_resource = raw_request.source_resource
    assert source_resource.namespace == "pyingestkit.resource.http"
    assert source_resource.locator == "https://api.example.test/customers.csv?page=2"
    assert ("status_code", "200") in source_resource.metadata
    assert ("etag", '"customers-v1"') in source_resource.metadata
    assert (
        "last_modified",
        "Wed, 02 Sep 2026 10:00:00 GMT",
    ) in source_resource.metadata

    persisted_evidence = "\n".join(
        [
            source_resource.locator or "",
            repr(source_resource.metadata),
            repr(raw_request.metadata),
        ]
    )
    assert wire_secret not in persisted_evidence
    assert "response-secret" not in persisted_evidence
    assert "Authorization" not in persisted_evidence
    assert "Set-Cookie" not in persisted_evidence

    raw_path = (
        tmp_path
        / "artifact-store"
        / "runs"
        / str(result.ingestion_run_id)
        / "raw"
        / "source.raw"
    )
    assert raw_path.read_bytes() == b"id,name\n1,Ada\n"
