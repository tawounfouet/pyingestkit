from __future__ import annotations

import unittest

from pyingestkit import Dataset, DatasetContract, FieldContract


class DatasetContractV2Tests(unittest.TestCase):
    def test_value_constraints_are_collected_without_coercion(self) -> None:
        dataset = Dataset(
            [
                {
                    "postal_code": "75001",
                    "country": "FR",
                    "score": 10,
                    "label": "Paris",
                },
                {
                    "postal_code": "75A01",
                    "country": "DE",
                    "score": -1,
                    "label": "x",
                },
                {
                    "postal_code": "750012",
                    "country": "FR",
                    "score": 101,
                    "label": "toolong",
                },
            ]
        )
        before = dataset.to_rows()
        result = DatasetContract(
            fields=(
                FieldContract(
                    "postal_code",
                    expected_type=str,
                    pattern=r"^\d{5}$",
                    min_length=5,
                    max_length=5,
                ),
                FieldContract("country", allowed_values={"FR", "BE", "CH"}),
                FieldContract("score", expected_type=int, min_value=0, max_value=100),
                FieldContract("label", expected_type=str, min_length=2, max_length=6),
            )
        ).validate(dataset)

        codes = [issue.code for issue in result.issues]
        self.assertIn("field.pattern", codes)
        self.assertIn("field.allowed_values", codes)
        self.assertIn("field.min_value", codes)
        self.assertIn("field.max_value", codes)
        self.assertIn("field.min_length", codes)
        self.assertIn("field.max_length", codes)
        self.assertEqual(dataset.to_rows(), before)

    def test_csv_like_string_is_not_coerced_for_numeric_constraint(self) -> None:
        dataset = Dataset([{"age": "42"}])
        result = DatasetContract(
            fields=(FieldContract("age", expected_type=int, min_value=0, max_value=130),)
        ).validate(dataset)

        self.assertEqual([issue.code for issue in result.issues], ["field.type"])
        self.assertEqual(dataset[0]["age"], "42")

    def test_pattern_is_full_match_and_requires_string(self) -> None:
        dataset = Dataset([{"code": "x123x"}, {"code": 123}])
        result = DatasetContract(fields=(FieldContract("code", pattern=r"\d{3}"),)).validate(
            dataset
        )

        self.assertEqual(
            [issue.code for issue in result.issues], ["field.pattern", "field.pattern"]
        )
        self.assertEqual(result.issues[1].context["requires_string"], True)

    def test_composite_uniqueness_reports_second_occurrence(self) -> None:
        dataset = Dataset(
            [
                {"country": "FR", "code": "75001"},
                {"country": "FR", "code": "69001"},
                {"country": "FR", "code": "75001"},
            ]
        )
        result = DatasetContract(unique_together=(("country", "code"),)).validate(dataset)

        issue = result.issues[0]
        self.assertEqual(issue.code, "dataset.unique_together")
        self.assertEqual(issue.row_index, 2)
        self.assertEqual(issue.context["first_row_index"], 0)

    def test_primary_key_requires_non_null_unique_combination(self) -> None:
        dataset = Dataset(
            [
                {"country": "FR", "code": "75001"},
                {"country": "FR", "code": None},
                {"country": "FR", "code": "75001"},
                {"country": "FR"},
            ]
        )
        result = DatasetContract(primary_key=("country", "code")).validate(dataset)
        codes = [issue.code for issue in result.issues]

        self.assertEqual(codes.count("key.null"), 2)
        self.assertEqual(codes.count("key.duplicate"), 1)

    def test_missing_primary_key_field_is_schema_issue(self) -> None:
        result = DatasetContract(primary_key=("id",)).validate(Dataset([{"name": "A"}]))

        self.assertEqual(result.issues[0].code, "dataset.required_field")
        self.assertEqual(result.issues[0].field, "id")

    def test_issue_limit_is_explicitly_reported(self) -> None:
        dataset = Dataset([{"value": value} for value in (1, 2, 3, 4)])
        result = DatasetContract(
            fields=(FieldContract("value", max_value=0),),
            max_issues=2,
        ).validate(dataset)

        self.assertEqual(result.issue_count, 2)
        self.assertTrue(result.issues_truncated)
        payload = result.as_dict()
        self.assertEqual(payload["issue_count"], 2)
        self.assertEqual(payload["issues_truncated"], True)

    def test_secret_value_preview_is_redacted_and_other_preview_is_bounded(self) -> None:
        dataset = Dataset(
            [
                {"api_token": "super-secret-token", "description": "x" * 200},
            ]
        )
        result = DatasetContract(
            fields=(
                FieldContract("api_token", allowed_values={"expected"}),
                FieldContract("description", max_length=10),
            )
        ).validate(dataset)

        token_issue, description_issue = result.issues
        self.assertEqual(token_issue.value_preview, "[REDACTED]")
        self.assertLessEqual(len(description_issue.value_preview or ""), 96)
        self.assertNotIn("super-secret-token", repr(result.as_dict()))

    def test_contract_definition_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            FieldContract("value", pattern="[")
        with self.assertRaises(ValueError):
            FieldContract("value", min_length=4, max_length=3)
        with self.assertRaises(ValueError):
            DatasetContract(unique_together=(("a",),))
        with self.assertRaises(ValueError):
            DatasetContract(primary_key=("id", "id"))
        with self.assertRaises(ValueError):
            DatasetContract(max_issues=0)


if __name__ == "__main__":
    unittest.main()
