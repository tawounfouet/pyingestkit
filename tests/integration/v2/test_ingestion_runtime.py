from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.decoders import CsvDecoder
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.runtime import IngestionStatus
from pyingestkit.domain.sources import Source
from pyingestkit.runtime.v2 import IngestionRuntime
from pyingestkit.stores import FileArtifactStore, FileDatasetVersionStore
from pyingestkit.validation.v2 import RequiredFieldV2


def _runtime(tmp_path: Path) -> tuple[IngestionRuntime, FileDatasetVersionStore]:
    sources = SourceRegistry()
    sources.register(
        FileSourceConnector(
            policy=FileAccessPolicy(
                allowed_roots=(tmp_path,),
                allowed_extensions=(".csv",),
            )
        )
    )
    decoders = DecoderRegistry()
    decoders.register(CsvDecoder())
    versions = FileDatasetVersionStore(root=tmp_path / "dataset-store")
    runtime = IngestionRuntime(
        sources=sources,
        decoders=decoders,
        artifacts=FileArtifactStore(root=tmp_path / "artifact-store"),
        versions=versions,
        publisher=versions,
        clock=lambda: datetime(2026, 10, 3, 9, 0, tzinfo=UTC),
    )
    return runtime, versions


def _definition(source_file: Path, *, decoder: str = "csv") -> IngestionDefinition:
    return IngestionDefinition(
        name="demo.customers",
        source=Source.file(path=str(source_file)),
        decoder=decoder,
        dataset="demo.customers",
    )


def test_runtime_executes_local_csv_to_published_dataset(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_bytes(b"id,name\n1,Ada\n")
    runtime, versions = _runtime(tmp_path)

    result = runtime.execute(
        _definition(source_file),
        validation_rules=(RequiredFieldV2("id"),),
        publish=True,
    )

    assert result.succeeded is True
    assert result.status is IngestionStatus.SUCCEEDED
    assert result.dataset_version is not None
    assert result.published_dataset is not None
    assert result.published_dataset.version.identity == result.dataset_version.identity
    assert versions.get_published("demo.customers") == result.published_dataset
    assert len(versions.read(result.dataset_version)) == 1


def test_runtime_can_store_version_without_publication(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_bytes(b"id,name\n1,Ada\n")
    runtime, versions = _runtime(tmp_path)

    result = runtime.execute(_definition(source_file), publish=False)

    assert result.succeeded is True
    assert result.dataset_version is not None
    assert result.published_dataset is None
    assert versions.get_published("demo.customers") is None


def test_runtime_validation_failure_does_not_create_dataset_version(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_bytes(b"id,name\n1,Ada\n")
    runtime, versions = _runtime(tmp_path)

    result = runtime.execute(
        _definition(source_file),
        validation_rules=(RequiredFieldV2("email"),),
    )

    assert result.succeeded is False
    assert result.status is IngestionStatus.FAILED
    assert result.failure is not None
    assert result.failure.error_code == "runtime.validation.failed"
    assert versions.list("demo.customers") == ()


def test_runtime_unknown_decoder_returns_configuration_failure(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_bytes(b"id,name\n1,Ada\n")
    runtime, versions = _runtime(tmp_path)

    result = runtime.execute(_definition(source_file, decoder="missing"))

    assert result.succeeded is False
    assert result.failure is not None
    assert result.failure.error_code == "runtime.decoder.configuration"
    assert versions.list("demo.customers") == ()
