from __future__ import annotations

import unittest

from pyingestkit.core.exceptions import ParseError
from pyingestkit.parsers import CsvParser


class CsvParserTests(unittest.TestCase):
    def test_parses_rows_without_type_or_whitespace_normalization(self) -> None:
        dataset = CsvParser().parse_bytes(b"id,name,active\n001, Alice ,true\n002,Bob,false\n")

        self.assertEqual(dataset.fields, ("id", "name", "active"))
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset[0]["id"], "001")
        self.assertEqual(dataset[0]["name"], " Alice ")
        self.assertEqual(dataset[0]["active"], "true")

    def test_header_only_csv_preserves_schema(self) -> None:
        dataset = CsvParser().parse_bytes(b"id,name\n")

        self.assertEqual(dataset.fields, ("id", "name"))
        self.assertEqual(dataset.row_count, 0)

    def test_custom_delimiter_is_structural_parsing(self) -> None:
        dataset = CsvParser(delimiter=";").parse_bytes(b"id;name\n1;Alice\n")

        self.assertEqual(dataset.to_rows(), [{"id": "1", "name": "Alice"}])

    def test_rejects_duplicate_headers(self) -> None:
        with self.assertRaises(ParseError):
            CsvParser().parse_bytes(b"id,id\n1,2\n")

    def test_rejects_row_width_mismatch(self) -> None:
        with self.assertRaises(ParseError):
            CsvParser().parse_bytes(b"id,name\n1,Alice,extra\n")


if __name__ == "__main__":
    unittest.main()
