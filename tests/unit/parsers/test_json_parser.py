from __future__ import annotations

import unittest

from pyingestkit.core.exceptions import ParseError
from pyingestkit.parsers import JsonParser


class JsonParserTests(unittest.TestCase):
    def test_parses_array_of_objects_preserving_json_types(self) -> None:
        dataset = JsonParser().parse_bytes(
            b'[{"id": 1, "active": true, "tags": ["a"]}, {"id": 2, "active": false}]'
        )

        self.assertEqual(dataset.fields, ("id", "active", "tags"))
        self.assertEqual(dataset[0]["id"], 1)
        self.assertIs(dataset[0]["active"], True)
        self.assertEqual(dataset[0]["tags"], ["a"])

    def test_single_object_becomes_one_record_by_default(self) -> None:
        dataset = JsonParser().parse_bytes(b'{"id": 1, "name": "Alice"}')

        self.assertEqual(dataset.row_count, 1)
        self.assertEqual(dataset.to_rows(), [{"id": 1, "name": "Alice"}])

    def test_records_path_selects_nested_record_array(self) -> None:
        parser = JsonParser(records_path=("payload", "items"))
        dataset = parser.parse_bytes(b'{"payload": {"items": [{"id": 1}, {"id": 2}]}}')

        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset.fields, ("id",))

    def test_rejects_scalar_dataset(self) -> None:
        with self.assertRaises(ParseError):
            JsonParser().parse_bytes(b"42")

    def test_rejects_non_object_record(self) -> None:
        with self.assertRaises(ParseError):
            JsonParser().parse_bytes(b'[{"id": 1}, 2]')

    def test_can_require_array_semantics(self) -> None:
        with self.assertRaises(ParseError):
            JsonParser(allow_single_object=False).parse_bytes(b'{"id": 1}')


if __name__ == "__main__":
    unittest.main()
