from __future__ import annotations

import importlib.util
import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from pyingestkit.core.exceptions import ConfigurationError, ParseError
from pyingestkit.parsers import ParquetParser


class _FakeTable:
    def __init__(self, rows, names):
        self._rows = rows
        self.schema = SimpleNamespace(names=names)

    def to_pylist(self):
        return list(self._rows)


class _FakeParquetModule:
    def __init__(self, *, rows, names):
        self.rows = rows
        self.names = names
        self.requested_columns = None

    def ParquetFile(self, _buffer):
        return SimpleNamespace(metadata=SimpleNamespace(num_rows=len(self.rows)))

    def read_table(self, _buffer, *, columns=None):
        self.requested_columns = columns
        names = self.names if columns is None else tuple(columns)
        rows = self.rows
        if columns is not None:
            rows = [{key: row.get(key) for key in columns} for row in rows]
        return _FakeTable(rows, names)


class ParquetParserTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "pyarrow extra is not installed")
    def test_real_pyarrow_round_trip_when_extra_is_available(self) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        buffer = BytesIO()
        table = pa.Table.from_pylist(
            [{"id": 1, "name": " Alice ", "active": True}, {"id": 2, "name": "Bob"}]
        )
        pq.write_table(table, buffer)
        dataset = ParquetParser().parse_bytes(buffer.getvalue())
        self.assertEqual(dataset.fields, ("id", "name", "active"))
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset[0]["name"], " Alice ")
        self.assertIs(dataset[0]["active"], True)

    def test_optional_dependency_error_is_actionable(self) -> None:
        with patch("pyingestkit.parsers.parquet.importlib.import_module", side_effect=ImportError):
            with self.assertRaisesRegex(ConfigurationError, r"pyingestkit\[parquet\]"):
                ParquetParser().parse_bytes(b"not-used")

    def test_materializes_native_values_without_normalization(self) -> None:
        backend = _FakeParquetModule(
            rows=[{"id": 1, "name": " Alice ", "active": True}, {"id": 2, "name": "Bob"}],
            names=("id", "name", "active"),
        )
        with patch("pyingestkit.parsers.parquet.importlib.import_module", return_value=backend):
            dataset = ParquetParser().parse_bytes(b"fixture")
        self.assertEqual(dataset.fields, ("id", "name", "active"))
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset[0]["name"], " Alice ")
        self.assertIs(dataset[0]["active"], True)

    def test_column_projection_is_forwarded_to_backend(self) -> None:
        backend = _FakeParquetModule(rows=[{"id": 1, "name": "Alice"}], names=("id", "name"))
        with patch("pyingestkit.parsers.parquet.importlib.import_module", return_value=backend):
            dataset = ParquetParser(columns=("id",)).parse_bytes(b"fixture")
        self.assertEqual(backend.requested_columns, ["id"])
        self.assertEqual(dataset.fields, ("id",))
        self.assertEqual(dataset.to_rows(), [{"id": 1}])

    def test_max_rows_is_checked_before_materialization(self) -> None:
        backend = _FakeParquetModule(rows=[{"id": 1}, {"id": 2}], names=("id",))
        with patch("pyingestkit.parsers.parquet.importlib.import_module", return_value=backend):
            with self.assertRaisesRegex(ParseError, "configured max_rows"):
                ParquetParser(max_rows=1).parse_bytes(b"fixture")

    def test_invalid_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ParquetParser(columns=())
        with self.assertRaises(ValueError):
            ParquetParser(columns=("id", "id"))
        with self.assertRaises(ValueError):
            ParquetParser(max_rows=-1)


if __name__ == "__main__":
    unittest.main()
