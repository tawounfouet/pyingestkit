from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from pyingestkit.metadata import (
    DiffMetadataCapability,
    DiffRecord,
    MemoryMetadataStore,
    SQLiteMetadataStore,
)


class DiffMetadataCapabilityTests(unittest.TestCase):
    def test_memory_store_records_diff_without_changing_base_contract(self) -> None:
        store = MemoryMetadataStore()
        self.assertIsInstance(store, DiffMetadataCapability)
        record = DiffRecord(
            id=None,
            run_id="run-1",
            step_name="Compare",
            dataset_id="demo.dataset",
            previous_version_id="sha256-a",
            candidate_fingerprint="sha256-b",
            added_count=1,
            removed_count=2,
            changed_count=3,
            unchanged_count=4,
            entries_truncated=False,
            report_path="reports/diff.json",
            created_at=datetime.now(UTC),
        )
        store.record_dataset_diff(record)
        rows = store.list_dataset_diffs("run-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, 1)

    def test_sqlite_schema_adds_dataset_diffs_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "pyingest.sqlite3"
            store = SQLiteMetadataStore(path)
            self.assertIsInstance(store, DiffMetadataCapability)
            with closing(sqlite3.connect(path)) as connection:
                rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
                names = {row[0] for row in rows}
            self.assertIn("dataset_diffs", names)


if __name__ == "__main__":
    unittest.main()
