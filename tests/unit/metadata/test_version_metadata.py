from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime

from pyingestkit.metadata import DatasetVersionRecord, PublishedDatasetRecord, SQLiteMetadataStore


class VersionMetadataTests(unittest.TestCase):
    def test_sqlite_additive_version_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SQLiteMetadataStore.for_workspace(tmp)
            store.record_dataset_version(
                DatasetVersionRecord(
                    dataset_id="demo.x",
                    version_id="sha256-" + "a" * 64,
                    fingerprint="sha256-" + "a" * 64,
                    snapshot_uri="versions/demo/x/a.json",
                    created_from_run_id="r1",
                    job_id="demo.x",
                    job_version="1",
                    source_artifact_id=None,
                    source_raw_sha256=None,
                    created_at=datetime.now(UTC),
                )
            )
            self.assertEqual(len(store.list_dataset_versions("demo.x")), 1)
            published = PublishedDatasetRecord(
                "demo.x", "sha256-" + "a" * 64, "r1", datetime.now(UTC)
            )
            store.record_published_dataset(published)
            self.assertEqual(store.get_published_dataset("demo.x").version_id, published.version_id)  # type: ignore[union-attr]
