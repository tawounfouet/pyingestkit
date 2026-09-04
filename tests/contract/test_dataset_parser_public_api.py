from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

import pyingestkit
import pyingestkit.contracts as contracts_api
import pyingestkit.parsers as parsers_api
import pyingestkit.validation as validation_api


class DatasetParserPublicApiTests(unittest.TestCase):
    def test_structured_parser_types_are_public(self) -> None:
        expected = {
            "CsvParser",
            "Dataset",
            "DatasetContract",
            "ExcelParser",
            "FieldContract",
            "Job",
            "JobDefinition",
            "JsonParser",
            "NdjsonParser",
            "ParquetParser",
            "Pipeline",
            "RunContext",
            "RunResult",
            "RunStatus",
            "Runner",
            "Step",
            "StepDefinition",
            "StepInvocation",
            "StepResult",
            "ValidationIssue",
            "ValidationResult",
            "job",
            "step",
        }
        self.assertTrue(expected.issubset(set(pyingestkit.__all__)))

    def test_namespace_contracts_are_explicit(self) -> None:
        self.assertEqual(
            set(parsers_api.__all__),
            {
                "CsvParser",
                "ExcelParser",
                "JsonParser",
                "JsonPathPart",
                "NdjsonParser",
                "ParquetParser",
                "Parser",
            },
        )
        self.assertEqual(
            set(contracts_api.__all__), {"DatasetContract", "ExpectedType", "FieldContract"}
        )
        self.assertIn("ValidationIssue", validation_api.__all__)
        self.assertIn("ValidationResult", validation_api.__all__)

    def test_dataframe_engines_are_not_mandatory_core_dependencies(self) -> None:
        root = Path(__file__).resolve().parents[2]
        config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        runtime_dependencies = "\n".join(config["project"]["dependencies"]).lower()
        self.assertNotIn("pandas", runtime_dependencies)
        self.assertNotIn("polars", runtime_dependencies)
        self.assertNotIn("pyarrow", runtime_dependencies)
        parquet_dependencies = "\n".join(config["project"]["optional-dependencies"]["parquet"])
        self.assertIn("pyarrow", parquet_dependencies.lower())

    def test_core_does_not_import_dataframe_engines_eagerly(self) -> None:
        root = Path(__file__).resolve().parents[2]
        runtime_source = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (root / "src" / "pyingestkit").rglob("*.py")
        )
        for forbidden in ("import pandas", "from pandas", "import polars", "from polars"):
            self.assertNotIn(forbidden, runtime_source)
        self.assertNotIn("import pyarrow", runtime_source)
        self.assertNotIn("from pyarrow", runtime_source)


if __name__ == "__main__":
    unittest.main()
