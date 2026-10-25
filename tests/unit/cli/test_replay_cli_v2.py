from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from typer.testing import CliRunner

from pyingestkit.adapters.filesystem import FileArtifactStore, FileDatasetVersionStore
from pyingestkit.adapters.formats.json import JsonDecoder
from pyingestkit.application.decoders import DecoderRegistry
from pyingestkit.application.runtime import IngestionRuntime
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.cli.app import app
from pyingestkit.domain.artifacts import (
    ArtifactKind,
    ArtifactRetention,
    PutArtifactRequest,
)
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source

_NOW = datetime(2026, 10, 25, 8, 0, 0, tzinfo=UTC)


def _setup_workspace_with_dataset(tmp_path: Path) -> tuple[str, str, str]:
    config_file = tmp_path / "pyingest.yaml"
    config_file.write_text(
        f"""
runtime:
  workspace: {tmp_path}
artifacts:
  backend: local
metadata:
  backend: sqlite
"""
    )

    artifact_store = FileArtifactStore(root=tmp_path)
    version_store = FileDatasetVersionStore(root=tmp_path)

    source_run_id = IngestionRunId.new()
    raw_content = b'{"records": [{"id": 1, "sku": "A1"}]}'
    raw_put = artifact_store.put(
        PutArtifactRequest(
            ingestion_run_id=source_run_id,
            correlation=CorrelationContext(ingestion_run_id=str(source_run_id)),
            kind=ArtifactKind.RAW,
            name="test.raw",
            content=raw_content,
            media_type="application/json",
            source_resource=ResourceReference(
                namespace="test",
                resource_id="res-1",
                locator="file:///tmp/test.json",
            ),
            source_acquired_at=_NOW,
            retention=ArtifactRetention(retain=True),
        )
    )
    assert raw_put.reference is not None

    decoders = DecoderRegistry()
    decoders.register(JsonDecoder())
    runtime = IngestionRuntime(
        sources=SourceRegistry(),
        decoders=decoders,
        artifacts=artifact_store,
        versions=version_store,
        publisher=version_store,
        clock=lambda: _NOW,
    )
    definition = IngestionDefinition(
        name="orders_ingest",
        source=Source.file(path="/tmp/test.json"),
        decoder="json",
        dataset="orders",
    )
    ingestion = runtime.execute_from_raw(
        definition,
        raw_artifact=raw_put.reference,
        raw_content=raw_content,
        publish=True,
        ingestion_run_id=source_run_id,
        correlation=CorrelationContext(ingestion_run_id=str(source_run_id)),
    )
    assert ingestion.dataset_version is not None
    version_id = ingestion.dataset_version.version_id
    return "orders", version_id, str(source_run_id)


def test_replay_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["replay", "--help"])
    assert result.exit_code == 0
    assert "--dataset" in result.output
    assert "-d" in result.output
    assert "--version" in result.output
    assert "-v" in result.output
    assert "--publish" in result.output


def test_replay_cli_version_requires_dataset() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["replay", "-v", "sha256-abcdef"])
    assert result.exit_code == 2
    assert "Missing option '--dataset' / '-d'" in result.output


def test_replay_cli_provenance_execution(tmp_path: Path) -> None:
    dataset_id, version_id, source_run_id = _setup_workspace_with_dataset(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "replay",
            "-d",
            dataset_id,
            "-v",
            version_id,
            "--workspace",
            str(tmp_path),
            "--config",
            str(tmp_path / "pyingest.yaml"),
        ],
    )
    assert result.exit_code == 0
    assert "Replay Provenance Execution" in result.output
    assert "MATCHED" in result.output
    assert dataset_id in result.output


def test_replay_cli_provenance_json_with_publish(tmp_path: Path) -> None:
    dataset_id, version_id, source_run_id = _setup_workspace_with_dataset(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "replay",
            "-d",
            dataset_id,
            "-v",
            version_id,
            "--publish",
            "--json",
            "--workspace",
            str(tmp_path),
            "--config",
            str(tmp_path / "pyingest.yaml"),
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["dataset_id"] == dataset_id
    assert data["version_id"] == version_id
    assert data["source_run_id"] == source_run_id
    assert data["matched"] is True
    assert data["succeeded"] is True
    assert data["published"] is True
    assert data["publication_status"] == "succeeded"
    assert data["lineage_id"] is not None
