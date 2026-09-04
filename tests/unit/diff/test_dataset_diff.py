from __future__ import annotations

import unittest

from pyingestkit import Dataset, DatasetDiffer, DiffKind, DiffPolicy
from pyingestkit.core.exceptions import DiffError


class DatasetDiffTests(unittest.TestCase):
    def test_keyed_diff_counts_added_removed_changed_and_unchanged(self) -> None:
        previous = Dataset(
            [
                {"id": 1, "name": "A", "meta": {"x": 1}},
                {"id": 2, "name": "B", "meta": None},
                {"id": 3, "name": "C", "meta": "same"},
            ]
        )
        candidate = Dataset(
            [
                {"id": 1, "name": "A2", "meta": {"x": 1}},
                {"id": 3, "name": "C", "meta": "same"},
                {"id": 4, "name": "D", "meta": None},
            ]
        )
        result = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(previous, candidate)
        self.assertEqual(
            (
                result.added_count,
                result.removed_count,
                result.changed_count,
                result.unchanged_count,
            ),
            (1, 1, 1, 1),
        )
        self.assertEqual(
            [entry.kind for entry in result.entries],
            [DiffKind.ADDED, DiffKind.REMOVED, DiffKind.CHANGED],
        )
        self.assertEqual(result.entries[-1].changed_fields, ("name",))

    def test_composite_key_ignore_and_compare_fields(self) -> None:
        previous = Dataset([{"country": "FR", "id": 1, "value": 10, "updated_at": "a"}])
        candidate = Dataset([{"country": "FR", "id": 1, "value": 11, "updated_at": "b"}])
        ignored = DatasetDiffer(
            DiffPolicy(key_fields=("country", "id"), ignore_fields=("updated_at",))
        ).compare(previous, candidate)
        self.assertEqual(ignored.changed_count, 1)
        self.assertEqual(ignored.entries[0].changed_fields, ("value",))
        compared = DatasetDiffer(
            DiffPolicy(key_fields=("country", "id"), compare_fields=("updated_at",))
        ).compare(previous, candidate)
        self.assertEqual(compared.entries[0].changed_fields, ("updated_at",))

    def test_duplicate_null_and_missing_keys_fail(self) -> None:
        valid = Dataset([{"id": 1, "v": "a"}])
        duplicate = Dataset([{"id": 1}, {"id": 1}])
        null = Dataset([{"id": None}])
        missing = Dataset([{"v": "x"}], fields=("id", "v"))
        differ = DatasetDiffer(DiffPolicy(key_fields=("id",)))
        with self.assertRaisesRegex(DiffError, "duplicate key"):
            differ.compare(duplicate, valid)
        with self.assertRaisesRegex(DiffError, "null key"):
            differ.compare(null, valid)
        with self.assertRaisesRegex(DiffError, "missing key"):
            differ.compare(missing, valid)

    def test_missing_is_different_from_none(self) -> None:
        previous = Dataset([{"id": 1}], fields=("id", "value"))
        candidate = Dataset([{"id": 1, "value": None}], fields=("id", "value"))
        result = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(previous, candidate)
        self.assertEqual(result.changed_count, 1)
        self.assertEqual(result.entries[0].changed_fields, ("value",))

    def test_schema_changes_are_reported(self) -> None:
        previous = Dataset([{"id": 1, "a": "x", "b": "y"}], fields=("id", "a", "b"))
        candidate = Dataset([{"id": 1, "b": "y", "c": "z"}], fields=("id", "b", "c"))
        result = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(previous, candidate)
        self.assertEqual(result.schema.added_fields, ("c",))
        self.assertEqual(result.schema.removed_fields, ("a",))
        self.assertFalse(result.schema.field_order_changed)
        self.assertEqual(result.changed_count, 1)

    def test_keyless_multiset_respects_duplicate_multiplicity_and_order(self) -> None:
        previous = Dataset([{"v": [1]}, {"v": [1]}, {"v": [2]}])
        candidate = Dataset([{"v": [2]}, {"v": [1]}, {"v": [3]}])
        result = DatasetDiffer().compare(previous, candidate)
        self.assertEqual(
            (
                result.added_count,
                result.removed_count,
                result.changed_count,
                result.unchanged_count,
            ),
            (1, 1, 0, 2),
        )
        reordered = DatasetDiffer().compare(
            Dataset([{"v": 1}, {"v": 2}]), Dataset([{"v": 2}, {"v": 1}])
        )
        self.assertFalse(reordered.has_changes)

    def test_max_entries_bounds_details_but_not_counts(self) -> None:
        previous = Dataset([{"id": value, "v": "old"} for value in range(5)])
        candidate = Dataset([{"id": value, "v": "new"} for value in range(5)])
        result = DatasetDiffer(DiffPolicy(key_fields=("id",), max_entries=2)).compare(
            previous, candidate
        )
        self.assertEqual(result.changed_count, 5)
        self.assertEqual(len(result.entries), 2)
        self.assertTrue(result.entries_truncated)

    def test_capture_values_is_opt_in_and_inputs_are_not_mutated(self) -> None:
        previous = Dataset([{"id": 1, "v": "old"}])
        candidate = Dataset([{"id": 1, "v": "new"}])
        before_previous = previous.to_rows()
        hidden = DatasetDiffer(DiffPolicy(key_fields=("id",))).compare(previous, candidate)
        self.assertIsNone(hidden.entries[0].before)
        shown = DatasetDiffer(DiffPolicy(key_fields=("id",), capture_values=True)).compare(
            previous, candidate
        )
        self.assertEqual(shown.entries[0].before["v"], "old")
        self.assertEqual(previous.to_rows(), before_previous)


if __name__ == "__main__":
    unittest.main()
