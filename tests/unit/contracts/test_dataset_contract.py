from __future__ import annotations

import unittest

from pyingestkit import Dataset, DatasetContract, FieldContract, ValidationResult


class DatasetContractTests(unittest.TestCase):
    def test_valid_dataset_returns_validation_result(self) -> None:
        dataset = Dataset([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
        contract = DatasetContract(
            fields=(
                FieldContract("id", nullable=False, expected_type=int, unique=True),
                FieldContract("name", nullable=False, expected_type=str),
            ),
            allow_extra_fields=False,
            min_rows=1,
        )
        result = contract.validate(dataset)
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)

    def test_reports_schema_row_null_type_unique_and_extra_issues(self) -> None:
        dataset = Dataset(
            [
                {"id": 1, "name": None, "extra": "x"},
                {"id": 1, "name": 42, "extra": "y"},
                {"name": "C", "extra": "z"},
            ]
        )
        contract = DatasetContract(
            fields=(
                FieldContract("id", nullable=False, expected_type=int, unique=True),
                FieldContract("name", nullable=False, expected_type=str),
                FieldContract("country", required=True),
            ),
            allow_extra_fields=False,
        )
        result = contract.validate(dataset)
        codes = [issue.code for issue in result.issues]
        self.assertFalse(result.is_valid)
        self.assertIn("field.required", codes)
        self.assertIn("field.null", codes)
        self.assertIn("field.type", codes)
        self.assertIn("field.unique", codes)
        self.assertIn("dataset.extra_field", codes)
        self.assertTrue(
            any(issue.row_index == 2 and issue.field == "id" for issue in result.issues)
        )

    def test_row_bounds_are_contract_concerns(self) -> None:
        dataset = Dataset([{"id": 1}])
        too_small = DatasetContract(min_rows=2).validate(dataset)
        too_large = DatasetContract(max_rows=0).validate(dataset)
        self.assertEqual(too_small.issues[0].code, "dataset.min_rows")
        self.assertEqual(too_large.issues[0].code, "dataset.max_rows")

    def test_contract_validation_does_not_mutate_dataset(self) -> None:
        dataset = Dataset([{"id": "001", "name": " Alice "}])
        before = dataset.to_rows()
        DatasetContract(
            fields=(FieldContract("id", expected_type=int), FieldContract("name"))
        ).validate(dataset)
        self.assertEqual(dataset.to_rows(), before)


if __name__ == "__main__":
    unittest.main()
