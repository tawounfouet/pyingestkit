from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit.core.exceptions import VersionStoreError
from pyingestkit.dataset import Dataset
from pyingestkit.metadata import MemoryMetadataStore
from pyingestkit.versioning import FilesystemDatasetVersionStore


class FilesystemDatasetVersionStoreTests(unittest.TestCase):
    def test_versions_are_content_addressed_immutable_and_publish_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            metadata = MemoryMetadataStore()
            store = FilesystemDatasetVersionStore(tmp, metadata_store=metadata)
            first = store.create_version(
                Dataset([{"id": 1, "name": "A"}]),
                dataset_id="demo.reference",
                created_from_run_id="run-1",
                job_id="demo.reference",
                job_version="1.0.0",
            )
            same = store.create_version(
                Dataset([{"id": 1, "name": "A"}]),
                dataset_id="demo.reference",
                created_from_run_id="run-2",
                job_id="demo.reference",
                job_version="1.0.0",
            )
            second = store.create_version(
                Dataset([{"id": 1, "name": "B"}]),
                dataset_id="demo.reference",
                created_from_run_id="run-3",
                job_id="demo.reference",
                job_version="1.0.1",
            )
            self.assertEqual(first.version_id, same.version_id)
            self.assertNotEqual(first.version_id, second.version_id)
            self.assertEqual(len(store.list_versions("demo.reference")), 2)
            self.assertEqual(store.load_dataset(first).to_rows(), [{"id": 1, "name": "A"}])

            published_first = store.publish(first, run_id="run-1")
            published_same = store.publish(first, run_id="run-2")
            self.assertEqual(published_first.published_at, published_same.published_at)
            current = store.publish(second, run_id="run-3")
            self.assertEqual(current.version_id, second.version_id)
            self.assertEqual(len(store.list_versions("demo.reference")), 2)
            pointer = Path(tmp) / "published" / "demo" / "reference" / "current.json"
            self.assertEqual(json.loads(pointer.read_text())["version_id"], second.version_id)
            self.assertEqual(len(metadata.dataset_version_runs), 3)

    def test_path_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FilesystemDatasetVersionStore(tmp)
            with self.assertRaises(VersionStoreError):
                store.create_version(
                    Dataset([{"id": 1}]),
                    dataset_id="../escape",
                    created_from_run_id="r",
                    job_id="x",
                    job_version="1",
                )
