from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

import pytest

from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.datasets import DatasetVersionReference, build_dataset_version
from pyingestkit.decoders import CsvDecoder, DecodeRequest, DecodeStatus
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.artifacts import (
    ArtifactIntegrityError,
    ArtifactPutStatus,
    ArtifactReference,
    PutArtifactRequest,
)
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source
from pyingestkit.replay.v2 import ReplayRequest, ReplayServiceV2
from pyingestkit.runtime.v2 import IngestionRuntime
from pyingestkit.stores import FileArtifactStore, FileDatasetVersionStore
from pyingestkit.validation.v2 import RequiredFieldV2


_NOW = datetime(2026, 10, 3, 10, 0, tzinfo=UTC)


def _artifact_path(reference: ArtifactReference) -> Path:
    locator = reference.resource.locator
    assert locator is not None
    parsed = urlsplit(locator)
    return Path(url2pathname(unquote(parsed.path)))


def _origin(
    tmp_path: Path,
) -> tuple[
    IngestionDefinition,
    IngestionRunId,
    ArtifactReference,
    DatasetVersionReference,
    FileArtifactStore,
    FileDatasetVersionStore,
]:
    source_file = tmp_path / "customers.csv"
    content = b"id,name\n1,Ada\n"
    source_file.write_bytes(content)
    definition = IngestionDefinition(
        name="demo.customers",
        source=Source.file(path=str(source_file)),
        decoder="csv",
        dataset="demo.customers",
    )
    source_run_id = IngestionRunId.new()
    correlation = CorrelationContext(ingestion_run_id=str(source_run_id))
    connector = FileSourceConnector(
        policy=FileAccessPolicy(
            allowed_roots=(tmp_path,),
            allowed_extensions=(".csv",),
        )
    )
    acquisition = connector.acquire(
        AcquisitionRequest(
            source=definition.source,
            ingestion_run_id=source_run_id,
            correlation=correlation,
        )
    )
    assert acquisition.status is AcquisitionStatus.SUCCEEDED

    artifacts = FileArtifactStore(root=tmp_path / "artifact-store")
    raw_put = artifacts.put(PutArtifactRequest.from_acquisition(acquisition, name="source.raw"))
    assert raw_put.status is ArtifactPutStatus.SUCCEEDED
    assert raw_put.reference is not None
    origin_raw = raw_put.reference

    decode_request = DecodeRequest(
        ingestion_run_id=source_run_id,
        correlation=correlation,
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
    versions = FileDatasetVersionStore(root=tmp_path / "dataset-store")
    expected = versions.put(version)
    versions.publish(
        expected,
        ingestion_run_id=source_run_id,
        published_at=_NOW,
    )
    source_file.unlink()
    return definition, source_run_id, origin_raw, expected, artifacts, versions


def _replay_service(
    artifacts: FileArtifactStore,
    versions: FileDatasetVersionStore,
) -> ReplayServiceV2:
    decoders = DecoderRegistry()
    decoders.register(CsvDecoder())
    runtime = IngestionRuntime(
        sources=SourceRegistry(),
        decoders=decoders,
        artifacts=artifacts,
        versions=versions,
        publisher=versions,
        clock=lambda: _NOW,
    )
    return ReplayServiceV2(runtime=runtime, clock=lambda: _NOW)


def test_strict_replay_uses_historical_raw_without_live_source(tmp_path: Path) -> None:
    definition, source_run_id, origin_raw, expected, artifacts, versions = _origin(tmp_path)
    published_before = versions.get_published(definition.dataset)
    service = _replay_service(artifacts, versions)

    replay = service.replay(
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
    assert replay.replay_raw_artifact.artifact_id != origin_raw.artifact_id
    assert replay.replay_raw_artifact.checksum == origin_raw.checksum
    assert replay.ingestion.dataset_version == expected
    assert replay.ingestion.published_dataset is None
    assert versions.get_published(definition.dataset) == published_before


def test_strict_replay_version_mismatch_fails_before_new_version_persistence(
    tmp_path: Path,
) -> None:
    definition, source_run_id, origin_raw, expected, artifacts, versions = _origin(tmp_path)
    service = _replay_service(artifacts, versions)
    wrong_version_id = "sha256-" + "f" * 64
    wrong_expected = DatasetVersionReference(
        dataset_id=definition.dataset,
        version_id=wrong_version_id,
        created_at=_NOW,
        schema_fingerprint=expected.schema_fingerprint,
        content_fingerprint=wrong_version_id,
    )
    history_before = versions.list(definition.dataset)

    replay = service.replay(
        ReplayRequest(
            source_run_id=source_run_id,
            definition=definition,
            origin_raw_artifact=origin_raw,
            expected_dataset_version=wrong_expected,
        )
    )

    assert replay.succeeded is False
    assert replay.matched is False
    assert replay.ingestion.failure is not None
    assert replay.ingestion.failure.error_code == "runtime.version_mismatch"
    assert replay.ingestion.dataset_version is None
    assert versions.list(definition.dataset) == history_before


def test_strict_replay_rejects_tampered_historical_raw(tmp_path: Path) -> None:
    definition, source_run_id, origin_raw, expected, artifacts, versions = _origin(tmp_path)
    _artifact_path(origin_raw).write_bytes(b"id,name\n1,Eve\n")
    service = _replay_service(artifacts, versions)

    with pytest.raises(ArtifactIntegrityError):
        service.replay(
            ReplayRequest(
                source_run_id=source_run_id,
                definition=definition,
                origin_raw_artifact=origin_raw,
                expected_dataset_version=expected,
            )
        )


def test_replay_rejects_source_run_id_reuse(tmp_path: Path) -> None:
    definition, source_run_id, origin_raw, expected, artifacts, versions = _origin(tmp_path)
    service = _replay_service(artifacts, versions)
    request = ReplayRequest(
        source_run_id=source_run_id,
        definition=definition,
        origin_raw_artifact=origin_raw,
        expected_dataset_version=expected,
    )

    with pytest.raises(ValueError, match="new IngestionRunId"):
        service.replay(request, ingestion_run_id=source_run_id)
