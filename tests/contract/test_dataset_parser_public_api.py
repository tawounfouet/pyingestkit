from __future__ import annotations

import unittest
from pathlib import Path

import pyingestkit
import pyingestkit.contracts as contracts_api
import pyingestkit.parsers as parsers_api
import pyingestkit.validation as validation_api


class DatasetParserPublicApiTests(unittest.TestCase):
    def test_beta1_top_level_api_contains_dataset_parser_contract_types(self) -> None:
        expected = {
            "CsvParser",
            "Dataset",
            "DatasetContract",
            "FieldContract",
            "Job",
            "JobDefinition",
            "JsonParser",
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
        self.assertEqual(set(pyingestkit.__all__), expected)

    def test_namespace_contracts_are_explicit(self) -> None:
        self.assertEqual(
            set(parsers_api.__all__), {"CsvParser", "JsonParser", "JsonPathPart", "Parser"}
        )
        self.assertEqual(
            set(contracts_api.__all__), {"DatasetContract", "ExpectedType", "FieldContract"}
        )
        self.assertIn("ValidationIssue", validation_api.__all__)
        self.assertIn("ValidationResult", validation_api.__all__)

    def test_framework_has_no_dataframe_dependency(self) -> None:
        root = Path(__file__).resolve().parents[2]
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8").lower()
        runtime_source = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (root / "src" / "pyingestkit").rglob("*.py")
        )
        for forbidden in ("pandas", "polars", "pyarrow"):
            self.assertNotIn(forbidden, pyproject)
            self.assertNotIn(f"import {forbidden}", runtime_source)
            self.assertNotIn(f"from {forbidden}", runtime_source)


if __name__ == "__main__":
    unittest.main()
