from __future__ import annotations

import unittest

from pyingestkit.core.exceptions import ParseError
from pyingestkit.parsers import NdjsonParser


class NdjsonParserTests(unittest.TestCase):
    def test_parses_objects_and_preserves_json_types(self) -> None:
        dataset = NdjsonParser().parse_bytes(
            b'{"id":1,"active":true,"tags":["a"]}\n{"id":2,"active":false}\n'
        )
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset.fields, ("id", "active", "tags"))
        self.assertEqual(dataset[0]["id"], 1)
        self.assertIs(dataset[0]["active"], True)
        self.assertEqual(dataset[0]["tags"], ["a"])

    def test_blank_lines_are_ignored_by_default(self) -> None:
        dataset = NdjsonParser().parse_bytes(b'\n{"id":1}\n\n{"id":2}\n')
        self.assertEqual(dataset.row_count, 2)

    def test_blank_lines_can_be_rejected(self) -> None:
        with self.assertRaises(ParseError):
            NdjsonParser(allow_blank_lines=False).parse_bytes(b'{"id":1}\n\n{"id":2}\n')

    def test_rejects_invalid_json_with_line_context(self) -> None:
        with self.assertRaisesRegex(ParseError, "line 2"):
            NdjsonParser().parse_bytes(b'{"id":1}\nnot-json\n')

    def test_rejects_non_object_records(self) -> None:
        with self.assertRaisesRegex(ParseError, "line 2"):
            NdjsonParser().parse_bytes(b'{"id":1}\n42\n')


if __name__ == "__main__":
    unittest.main()
