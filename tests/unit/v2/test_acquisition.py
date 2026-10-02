from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionStatus,
)
from pyingestkit.domain.runtime import (
    CorrelationContext,
    FailureCategory,
)
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source, SourceKind
from pyingestkit.ports.sources import (
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)


def _request(source: Source) -> AcquisitionRequest:
    run_id = IngestionRunId.new()
    return AcquisitionRequest(
        source=source,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
    )


def test_file_connector_acquires_bounded_content_with_evidence(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "customers.csv"
    content = b"id,name\n1,Ada\n"
    source_file.write_bytes(content)
    connector = FileSourceConnector(
        policy=FileAccessPolicy(
            allowed_roots=(tmp_path,),
            allowed_extensions=(".csv",),
        )
    )

    result = connector.acquire(_request(Source.file(path=str(source_file))))

    assert result.status is AcquisitionStatus.SUCCEEDED
    assert result.content == content
    assert result.size_bytes == len(content)
    assert result.checksum_algorithm == "sha256"
    assert result.checksum == hashlib.sha256(content).hexdigest()
    assert result.resource is not None
    assert result.resource.locator == source_file.resolve().as_uri()
    assert result.resource.namespace == "pyingestkit.resource.file"
    assert result.media_type in {"text/csv", "application/csv"}
    assert result.failure is None
    assert result.diagnostics[0].code == "acquisition.file.succeeded"
    assert result.acquired_at.tzinfo is UTC


def test_file_connector_supports_relative_paths_under_one_root(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "nested" / "customers.json"
    source_file.parent.mkdir()
    source_file.write_text('{"id": 1}', encoding="utf-8")
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,)))

    result = connector.acquire(_request(Source.file(path="nested/customers.json")))

    assert result.status is AcquisitionStatus.SUCCEEDED
    assert result.resource is not None
    assert result.resource.locator == source_file.resolve().as_uri()


def test_file_connector_rejects_path_outside_allowed_root(
    tmp_path: Path,
) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("id\n1\n", encoding="utf-8")
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(allowed,)))

    result = connector.acquire(_request(Source.file(path=str(outside))))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.AUTHORIZATION
    assert result.failure.error_code == "acquisition.file.outside_allowed_root"
    assert result.content is None


def test_file_connector_reports_missing_file_as_structured_failure(
    tmp_path: Path,
) -> None:
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,)))

    result = connector.acquire(_request(Source.file(path="missing.csv")))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.NOT_FOUND
    assert result.failure.error_code == "acquisition.file.not_found"


def test_file_connector_enforces_maximum_bytes(tmp_path: Path) -> None:
    source_file = tmp_path / "large.bin"
    source_file.write_bytes(b"12345")
    connector = FileSourceConnector(
        policy=FileAccessPolicy(
            allowed_roots=(tmp_path,),
            max_bytes=4,
        )
    )

    result = connector.acquire(_request(Source.file(path=str(source_file))))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.RESOURCE_EXHAUSTED


def test_file_connector_enforces_extension_policy(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.json"
    source_file.write_text("{}", encoding="utf-8")
    connector = FileSourceConnector(
        policy=FileAccessPolicy(
            allowed_roots=(tmp_path,),
            allowed_extensions=("csv",),
        )
    )

    result = connector.acquire(_request(Source.file(path=str(source_file))))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.file.extension_forbidden"


def test_file_connector_rejects_symlink_by_default(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_text("id\n1\n", encoding="utf-8")
    link = tmp_path / "customers-link.csv"
    try:
        link.symlink_to(source_file)
    except OSError:
        pytest.skip("Symlinks are not supported in this environment.")

    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,)))
    result = connector.acquire(_request(Source.file(path=str(link))))

    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.file.symlink_forbidden"


def test_file_policy_construction_performs_no_filesystem_validation(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "not-created"

    policy = FileAccessPolicy(allowed_roots=(missing_root,))
    connector = FileSourceConnector(policy=policy)

    result = connector.acquire(_request(Source.file(path="customers.csv")))
    assert result.status is AcquisitionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "acquisition.file.root_not_found"


def test_acquisition_request_rejects_mismatched_correlation() -> None:
    run_id = IngestionRunId.new()

    with pytest.raises(ValueError):
        AcquisitionRequest(
            source=Source.file(path="/data/customers.csv"),
            ingestion_run_id=run_id,
            correlation=CorrelationContext(ingestion_run_id="different-run"),
        )


class _SecondFileConnector:
    descriptor = SourceConnectorDescriptor(
        id="test.second-file",
        display_name="Second file",
        connector_version="1",
        supported_source_kinds=(SourceKind.FILE,),
        capabilities=(SourceConnectorCapability.ACQUIRE,),
    )

    def acquire(self, request: AcquisitionRequest):
        raise AssertionError("not used")


def test_source_registry_registration_is_explicit_and_deterministic(
    tmp_path: Path,
) -> None:
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,)))
    registry = SourceRegistry()

    registry.register(connector)

    assert len(registry) == 1
    assert registry.get("pyingestkit.file") is connector
    assert registry.resolve(Source.file(path="/data/customers.csv")) is connector
    assert registry.list() == (connector,)


def test_source_registry_rejects_duplicate_registration(tmp_path: Path) -> None:
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,)))
    registry = SourceRegistry()
    registry.register(connector)

    with pytest.raises(ValueError):
        registry.register(connector)


def test_source_registry_rejects_ambiguous_kind_resolution(
    tmp_path: Path,
) -> None:
    registry = SourceRegistry()
    registry.register(FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,))))
    registry.register(_SecondFileConnector())

    with pytest.raises(LookupError):
        registry.resolve(Source.file(path="/data/customers.csv"))


def test_acquisition_result_timestamp_is_timezone_aware(tmp_path: Path) -> None:
    source_file = tmp_path / "one.txt"
    source_file.write_text("one", encoding="utf-8")
    connector = FileSourceConnector(policy=FileAccessPolicy(allowed_roots=(tmp_path,)))

    result = connector.acquire(_request(Source.file(path=str(source_file))))

    assert isinstance(result.acquired_at, datetime)
    assert result.acquired_at.utcoffset() is not None
