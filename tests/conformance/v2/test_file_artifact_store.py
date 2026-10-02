from __future__ import annotations

from pathlib import Path

from pyingestkit.adapters.filesystem import FileArtifactStore
from pyingestkit.domain.artifacts import (
    ArtifactKind,
    ArtifactPutStatus,
    PutArtifactRequest,
)
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.ports.artifacts import ArtifactReader, ArtifactStore


def _request() -> PutArtifactRequest:
    run_id = IngestionRunId.new()
    return PutArtifactRequest(
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        kind=ArtifactKind.REPORT,
        name="report.json",
        content=b'{"ok":true}',
        media_type="application/json",
    )


def test_file_artifact_store_satisfies_port_contract(tmp_path: Path) -> None:
    store = FileArtifactStore(root=tmp_path / "artifacts")

    assert isinstance(store, ArtifactStore)


def test_file_artifact_store_put_open_exists_conformance(tmp_path: Path) -> None:
    store = FileArtifactStore(root=tmp_path / "artifacts")
    result = store.put(_request())

    assert result.status is ArtifactPutStatus.SUCCEEDED
    assert result.reference is not None
    assert store.exists(result.reference)

    reader = store.open(result.reference)
    assert isinstance(reader, ArtifactReader)
    assert reader.reference is result.reference
    assert reader.read() == b'{"ok":true}'
