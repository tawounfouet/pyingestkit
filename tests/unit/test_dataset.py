from __future__ import annotations

import unittest

from pyingestkit import Dataset


class DatasetTests(unittest.TestCase):
    def test_infers_stable_field_order_and_row_count(self) -> None:
        dataset = Dataset([{"id": 1, "name": "A"}, {"id": 2, "active": True}])

        self.assertEqual(dataset.fields, ("id", "name", "active"))
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(len(dataset), 2)

    def test_preserves_explicit_schema_for_empty_dataset(self) -> None:
        dataset = Dataset([], fields=("id", "name"))

        self.assertEqual(dataset.fields, ("id", "name"))
        self.assertEqual(dataset.row_count, 0)

    def test_rows_are_read_only_and_to_rows_returns_copies(self) -> None:
        dataset = Dataset([{"id": 1}])

        with self.assertRaises(TypeError):
            dataset[0]["id"] = 2  # type: ignore[index]

        rows = dataset.to_rows()
        rows[0]["id"] = 3
        self.assertEqual(dataset[0]["id"], 1)

    def test_explicit_schema_rejects_unknown_row_field(self) -> None:
        with self.assertRaises(ValueError):
            Dataset([{"id": 1, "name": "A"}], fields=("id",))


if __name__ == "__main__":
    unittest.main()
