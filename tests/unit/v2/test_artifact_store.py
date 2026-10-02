from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyingestkit.adapters.filesystem import (
    FileAccessPolicy,
    FileArtifactStore,
    FileSourceConnector,
)
from pyingestkit.domain.acquisition import AcquisitionRequest
from pyingestkit.domain.artifacts import (
    ArtifactIntegrityError,
    ArtifactKind,
    ArtifactPutStatus,
    ArtifactReference,
    ArtifactRetention,
    PutArtifactRequest,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, FailureCategory
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source


def _acquire(tmp_path: Path, content: bytes = b"id,name\n1,Ada\n"):
    source_file = tmp_path / "source" / "customers.csv"
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(content)
    run_id = IngestionRunId.new()
    request = AcquisitionRequest(
        source=Source.file(path=str(source_file)),
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    )
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(source_file.parent,)))
    return connector.acquire(request)


def test_file_artifact_store_persists_exact_acquired_bytes_as_raw(tmp_path: Path) -> None:
    acquisition = _acquire(tmp_path)
    store = FileArtifactStore(root=tmp_path / "artifacts")
    request = PutArtifactRequest.from_acquisition(
        acquisition,
        name="customers.csv",
        retention=ArtifactRetention(policy_id="raw-30d"),
        manifest_artifact_id="manifest-run-1",
        metadata=(("dataset", "customers"),),
    )

    result = store.put(request)

    assert result.status is ArtifactPutStatus.SUCCEEDED
    assert result.reference is not None
    assert result.reference.kind == ArtifactKind.RAW.value
    assert result.reference.checksum_algorithm == "sha256"
    assert result.reference.checksum == acquisition.checksum
    assert result.reference.size_bytes == acquisition.size_bytes
    assert result.reference.metadata == (("dataset", "customers"),)
    assert result.raw_evidence is not None
    assert result.raw_evidence.source_resource == acquisition.resource
    assert result.raw_evidence.retention.policy_id == "raw-30d"
    assert result.raw_evidence.manifest_artifact_id == "manifest-run-1"
    assert store.exists(result.reference)
    assert store.open(result.reference).read() == acquisition.content


def test_raw_artifact_path_is_create_once_and_existing_bytes_are_not_mutated(
    tmp_path: Path,
) -> None:
    acquisition = _acquire(tmp_path)
    store = FileArtifactStore(root=tmp_path / "artifacts")
    request = PutArtifactRequest.from_acquisition(acquisition, name="customers.csv")

    first = store.put(request)
    second = store.put(request)

    assert first.status is ArtifactPutStatus.SUCCEEDED
    assert second.status is ArtifactPutStatus.CONFLICT
    assert second.failure is not None
    assert second.failure.category is FailureCategory.CONFLICT
    assert first.reference is not None
    assert store.open(first.reference).read() == acquisition.content


def test_reader_detects_durable_byte_tampering(tmp_path: Path) -> None:
    acquisition = _acquire(tmp_path)
    store = FileArtifactStore(root=tmp_path / "artifacts")
    result = store.put(PutArtifactRequest.from_acquisition(acquisition, name="customers.csv"))
    assert result.reference is not None
    locator = result.reference.resource.locator
    assert locator is not None
    path = Path(locator.removeprefix("file://"))
    path.write_bytes(b"tampered")

    with pytest.raises(ArtifactIntegrityError):
        store.open(result.reference).read()


def test_store_rejects_acquisition_checksum_mismatch_before_write(tmp_path: Path) -> None:
    acquisition = _acquire(tmp_path)
    assert acquisition.content is not None
    assert acquisition.resource is not None
    request = PutArtifactRequest(
        ingestion_run_id=acquisition.ingestion_run_id,
        correlation=acquisition.correlation,
        kind=ArtifactKind.RAW,
        name="customers.csv",
        content=acquisition.content,
        media_type=acquisition.media_type,
        source_resource=acquisition.resource,
        source_acquired_at=acquisition.acquired_at,
        expected_checksum_algorithm="sha256",
        expected_checksum="0" * 64,
    )
    store = FileArtifactStore(root=tmp_path / "artifacts")

    result = store.put(request)

    assert result.status is ArtifactPutStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.INTEGRITY
    assert not (tmp_path / "artifacts").exists()


def test_file_artifact_store_constructor_performs_no_io(tmp_path: Path) -> None:
    root = tmp_path / "not-created"

    store = FileArtifactStore(root=root)

    assert store.root == root
    assert not root.exists()


def test_raw_artifact_evidence_is_immutable(tmp_path: Path) -> None:
    acquisition = _acquire(tmp_path)
    store = FileArtifactStore(root=tmp_path / "artifacts")
    result = store.put(
        PutArtifactRequest.from_acquisition(acquisition, name="customers.csv")
    )
    assert result.raw_evidence is not None

    with pytest.raises(FrozenInstanceError):
        result.raw_evidence.manifest_artifact_id = "changed"  # type: ignore[misc]


def test_file_artifact_store_rejects_reference_outside_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    uri = outside.resolve().as_uri()
    forged = ArtifactReference(
        artifact_id="forged",
        kind="raw",
        resource=ResourceReference(
            namespace="pyingestkit.artifact.file",
            resource_id=f"file_{hashlib.sha256(uri.encode('utf-8')).hexdigest()}",
            locator=uri,
        ),
        checksum_algorithm="sha256",
        checksum=hashlib.sha256(b"outside").hexdigest(),
        size_bytes=7,
        created_at=datetime(2026, 10, 2, tzinfo=UTC),
    )
    store = FileArtifactStore(root=tmp_path / "artifacts")

    with pytest.raises(ValueError):
        store.open(forged)


def test_non_raw_artifact_does_not_claim_raw_evidence(tmp_path: Path) -> None:
    run_id = IngestionRunId.new()
    correlation = CorrelationContext(ingestion_run_id=str(run_id))
    store = FileArtifactStore(root=tmp_path / "artifacts")
    request = PutArtifactRequest(
        ingestion_run_id=run_id,
        correlation=correlation,
        kind=ArtifactKind.REPORT,
        name="quality.json",
        content=b"{}",
        media_type="application/json",
    )

    result = store.put(request)

    assert result.status is ArtifactPutStatus.SUCCEEDED
    assert result.reference is not None
    assert result.raw_evidence is None
    assert store.open(result.reference).read() == b"{}"
