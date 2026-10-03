from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

import pytest

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.stores import FileDatasetVersionStore

from .test_dataset_version import _version


def _snapshot_path(reference: DatasetVersionReference) -> Path:
    assert reference.locator is not None
    assert reference.locator.locator is not None
    parsed = urlsplit(reference.locator.locator)
    return Path(url2pathname(unquote(parsed.path)))


def test_filesystem_store_round_trips_immutable_snapshot(tmp_path: Path) -> None:
    version = _version(b"id,name\n1,Ada\n")
    store = FileDatasetVersionStore(root=tmp_path)

    reference = store.put(version)
    restored = store.read(reference)

    assert reference.identity == version.reference.identity
    assert reference.schema_fingerprint == version.schema.fingerprint
    assert restored == version.representation
    assert store.get(version.dataset_id, version.version_id) == reference


def test_same_content_is_idempotent_across_runs(tmp_path: Path) -> None:
    first = _version(b"id,name\n1,Ada\n")
    second = _version(b"id,name\n1,Ada\n")
    store = FileDatasetVersionStore(root=tmp_path)

    first_reference = store.put(first)
    second_reference = store.put(second)

    assert first.ingestion_run_id != second.ingestion_run_id
    assert first_reference == second_reference
    assert store.list(first.dataset_id) == (first_reference,)


def test_changed_content_creates_distinct_version_history(tmp_path: Path) -> None:
    first = _version(b"id,name\n1,Ada\n")
    second = _version(b"id,name\n1,Linus\n")
    store = FileDatasetVersionStore(root=tmp_path)

    first_reference = store.put(first)
    second_reference = store.put(second)
    versions = store.list(first.dataset_id)

    assert {item.version_id for item in versions} == {
        first_reference.version_id,
        second_reference.version_id,
    }


def test_snapshot_tampering_fails_closed(tmp_path: Path) -> None:
    version = _version(b"id,name\n1,Ada\n")
    store = FileDatasetVersionStore(root=tmp_path)
    reference = store.put(version)
    snapshot = _snapshot_path(reference)

    snapshot.write_bytes(snapshot.read_bytes().replace(b"Ada", b"Eve"))

    with pytest.raises(ValueError, match="content fingerprint mismatch"):
        store.read(reference)


def test_publication_replaces_only_current_pointer(tmp_path: Path) -> None:
    first = _version(b"id,name\n1,Ada\n")
    second = _version(b"id,name\n1,Linus\n")
    store = FileDatasetVersionStore(root=tmp_path)
    first_reference = store.put(first)
    second_reference = store.put(second)
    first_run = IngestionRunId.new()
    second_run = IngestionRunId.new()

    published_first = store.publish(
        first_reference,
        ingestion_run_id=first_run,
        published_at=datetime(2026, 10, 2, 17, 0, tzinfo=UTC),
    )
    published_second = store.publish(
        second_reference,
        ingestion_run_id=second_run,
        published_at=datetime(2026, 10, 2, 17, 5, tzinfo=UTC),
    )

    assert published_first.version_id == first_reference.version_id
    assert published_second.version_id == second_reference.version_id
    assert store.get_published(first.dataset_id) == published_second
    assert store.read(first_reference) == first.representation


def test_republishing_same_version_is_idempotent(tmp_path: Path) -> None:
    version = _version(b"id\n1\n")
    store = FileDatasetVersionStore(root=tmp_path)
    reference = store.put(version)
    first_run = IngestionRunId.new()

    first = store.publish(
        reference,
        ingestion_run_id=first_run,
        published_at=datetime(2026, 10, 2, 17, 0, tzinfo=UTC),
    )
    second = store.publish(
        reference,
        ingestion_run_id=IngestionRunId.new(),
        published_at=datetime(2026, 10, 2, 18, 0, tzinfo=UTC),
    )

    assert second == first


def test_dataset_id_path_traversal_is_rejected(tmp_path: Path) -> None:
    version = _version(b"id\n1\n", dataset_id="../escape")
    store = FileDatasetVersionStore(root=tmp_path)

    with pytest.raises(ValueError, match="Invalid dataset_id"):
        store.put(version)
