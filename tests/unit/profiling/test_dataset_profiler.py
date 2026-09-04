from __future__ import annotations

import unittest

from pyingestkit import Dataset, DatasetProfiler


class DatasetProfilerTests(unittest.TestCase):
    def test_profile_is_structural_deterministic_and_non_mutating(self) -> None:
        dataset = Dataset(
            [
                {"id": 1, "name": "Paris", "tags": ["a", "b"]},
                {"id": 2, "name": None, "tags": ["a", "b"]},
                {"id": 2, "name": "Lyon", "tags": ["c"]},
            ],
            source_artifact_id="raw-123",
        )
        before = dataset.to_rows()

        profile = DatasetProfiler().profile(dataset)

        self.assertEqual(profile.row_count, 3)
        self.assertEqual(profile.field_count, 3)
        self.assertEqual([field.name for field in profile.fields], ["id", "name", "tags"])
        self.assertEqual(profile.source_artifact_id, "raw-123")
        self.assertEqual(dataset.to_rows(), before)

        id_profile = profile.fields[0]
        self.assertEqual(id_profile.present_count, 3)
        self.assertEqual(id_profile.null_count, 0)
        self.assertEqual(id_profile.non_null_count, 3)
        self.assertEqual(id_profile.distinct_count, 2)
        self.assertEqual(id_profile.observed_types, ("int",))
        self.assertEqual(id_profile.min_value, 1)
        self.assertEqual(id_profile.max_value, 2)

        name_profile = profile.fields[1]
        self.assertEqual(name_profile.null_count, 1)
        self.assertEqual(name_profile.distinct_count, 2)
        self.assertEqual(name_profile.min_length, 4)
        self.assertEqual(name_profile.max_length, 5)

        tags_profile = profile.fields[2]
        self.assertEqual(tags_profile.distinct_count, 2)
        self.assertIsNone(tags_profile.min_value)
        self.assertIsNone(tags_profile.min_length)

    def test_mixed_types_are_safe_and_observed_types_are_stable(self) -> None:
        dataset = Dataset([{"value": 1}, {"value": "1"}, {"value": 1.5}, {"value": None}])

        first = DatasetProfiler().profile(dataset).fields[0]
        second = DatasetProfiler().profile(dataset).fields[0]

        self.assertEqual(first.observed_types, ("NoneType", "float", "int", "str"))
        self.assertEqual(first.observed_types, second.observed_types)
        self.assertIsNone(first.min_value)
        self.assertIsNone(first.max_value)
        self.assertIsNone(first.min_length)
        self.assertIsNone(first.max_length)

    def test_sparse_rows_and_full_row_duplicates_are_counted(self) -> None:
        dataset = Dataset(
            [
                {"id": 1, "name": "A"},
                {"id": 1},
                {"id": 1},
                {"id": 1, "name": "A"},
            ]
        )
        profile = DatasetProfiler().profile(dataset)

        name_profile = profile.fields[1]
        self.assertEqual(name_profile.present_count, 2)
        self.assertEqual(name_profile.non_null_count, 2)
        self.assertEqual(profile.duplicate_row_count, 2)

    def test_nested_mapping_identity_is_order_independent(self) -> None:
        dataset = Dataset(
            [
                {"payload": {"a": 1, "b": [1, 2]}},
                {"payload": {"b": [1, 2], "a": 1}},
            ]
        )
        profile = DatasetProfiler().profile(dataset)

        self.assertEqual(profile.fields[0].distinct_count, 1)
        self.assertEqual(profile.duplicate_row_count, 1)


if __name__ == "__main__":
    unittest.main()
