from __future__ import annotations

import sqlite3
import tempfile
from contextlib import closing
import unittest
from pathlib import Path

from pyingestkit.metadata import SQLiteMetadataStore


class SQLiteStoreTests(unittest.TestCase):
    def test_schema_contains_foundation_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state" / "pyingest.sqlite3"
            SQLiteMetadataStore(path)
            with closing(sqlite3.connect(path)) as connection:
                names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ("runs", "steps", "artifacts", "validations", "publications", "events"):
                self.assertIn(table, names)

    def test_for_workspace_uses_standard_state_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            self.assertEqual(store.path, workspace / "state" / "pyingest.sqlite3")


if __name__ == "__main__":
    unittest.main()
