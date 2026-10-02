from __future__ import annotations

from pathlib import Path

from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionStatus
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source, SourceKind
from pyingestkit.ports.sources import (
    SourceConnector,
    SourceConnectorCapability,
)


def _request(source: Source) -> AcquisitionRequest:
    run_id = IngestionRunId.new()
    return AcquisitionRequest(
        source=source,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    )


def test_file_source_connector_satisfies_port_and_descriptor_contract(
    tmp_path: Path,
) -> None:
    connector = FileSourceConnector(
        policy=FileAccessPolicy(allowed_roots=(tmp_path,))
    )

    assert isinstance(connector, SourceConnector)
    assert connector.descriptor.id == "pyingestkit.file"
    assert connector.descriptor.supported_source_kinds == (SourceKind.FILE,)
    assert connector.descriptor.capabilities == (
        SourceConnectorCapability.ACQUIRE,
    )
    assert connector.descriptor.optional_dependencies_available is True


def test_file_source_connector_acquire_conformance(tmp_path: Path) -> None:
    source_file = tmp_path / "payload.csv"
    source_file.write_bytes(b"id\n1\n")
    connector = FileSourceConnector(
        policy=FileAccessPolicy(allowed_roots=(tmp_path,))
    )
    request = _request(Source.file(path=str(source_file)))

    result = connector.acquire(request)

    assert result.status is AcquisitionStatus.SUCCEEDED
    assert result.ingestion_run_id == request.ingestion_run_id
    assert result.correlation == request.correlation
    assert result.source_kind is SourceKind.FILE
    assert result.resource is not None
    assert result.content == b"id\n1\n"
    assert result.checksum_algorithm == "sha256"
    assert result.checksum
    assert result.size_bytes == len(result.content)
    assert result.failure is None
