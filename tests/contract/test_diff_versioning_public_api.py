from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

import pyingestkit
from pyingestkit.diff import DatasetDiff, DatasetDiffer, DiffEntry, DiffKind, DiffPolicy, SchemaDiff
from pyingestkit.versioning import (
    DatasetFingerprint,
    DatasetFingerprinter,
    DatasetFingerprintPolicy,
)


class DiffVersioningPublicApiTests(unittest.TestCase):
    def test_a1_types_are_top_level_and_namespaced(self) -> None:
        expected = {
            "DatasetDiff",
            "DatasetDiffer",
            "DatasetFingerprint",
            "DatasetFingerprinter",
            "DatasetFingerprintPolicy",
            "DiffEntry",
            "DiffKind",
            "DiffPolicy",
            "SchemaDiff",
        }
        self.assertTrue(expected.issubset(set(pyingestkit.__all__)))
        self.assertIs(pyingestkit.DatasetDiff, DatasetDiff)
        self.assertIs(pyingestkit.DatasetDiffer, DatasetDiffer)
        self.assertIs(pyingestkit.DatasetFingerprint, DatasetFingerprint)
        self.assertIs(pyingestkit.DatasetFingerprinter, DatasetFingerprinter)
        self.assertIs(pyingestkit.DatasetFingerprintPolicy, DatasetFingerprintPolicy)
        self.assertIs(pyingestkit.DiffEntry, DiffEntry)
        self.assertIs(pyingestkit.DiffKind, DiffKind)
        self.assertIs(pyingestkit.DiffPolicy, DiffPolicy)
        self.assertIs(pyingestkit.SchemaDiff, SchemaDiff)

    def test_a1_adds_no_mandatory_runtime_dependency(self) -> None:
        root = Path(__file__).resolve().parents[2]
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        dependencies = " ".join(data["project"]["dependencies"]).lower()
        for name in ("pandas", "polars", "duckdb", "deepdiff"):
            self.assertNotIn(name, dependencies)


if __name__ == "__main__":
    unittest.main()
