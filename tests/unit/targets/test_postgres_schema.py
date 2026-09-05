from __future__ import annotations

import unittest
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    BIGINT,
    BOOLEAN,
    DATE,
    DOUBLE_PRECISION,
    NUMERIC,
    TIMESTAMP,
    Column,
    LargeBinary,
    MetaData,
    Table,
    Text,
)

from pyingestkit import Dataset
from pyingestkit.targets.errors import TargetConfigurationError
from pyingestkit.targets.schema import PostgresSchemaMapper, PostgresValueType


class PostgresSchemaMapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = PostgresSchemaMapper()

    def test_mapping_is_deterministic_for_supported_python_values(self) -> None:
        dataset = Dataset(
            [
                {
                    "text_value": 'café\nquoted "text"',
                    "int_value": 42,
                    "float_value": 1.5,
                    "decimal_value": Decimal("1234567890.123456789"),
                    "bool_value": True,
                    "date_value": date(2026, 9, 4),
                    "naive_ts": datetime(2026, 9, 4, 12, 30),
                    "aware_ts": datetime(2026, 9, 4, 12, 30, tzinfo=UTC),
                    "bytes_value": b"\x00\x01payload",
                    "nullable": None,
                }
            ]
        )
        plan = self.mapper.plan(dataset)
        actual = {column.name: column.value_type for column in plan.columns}
        self.assertEqual(actual["text_value"], PostgresValueType.TEXT)
        self.assertEqual(actual["int_value"], PostgresValueType.BIGINT)
        self.assertEqual(actual["float_value"], PostgresValueType.DOUBLE_PRECISION)
        self.assertEqual(actual["decimal_value"], PostgresValueType.NUMERIC)
        self.assertEqual(actual["bool_value"], PostgresValueType.BOOLEAN)
        self.assertEqual(actual["date_value"], PostgresValueType.DATE)
        self.assertEqual(actual["naive_ts"], PostgresValueType.TIMESTAMP)
        self.assertEqual(actual["aware_ts"], PostgresValueType.TIMESTAMPTZ)
        self.assertEqual(actual["bytes_value"], PostgresValueType.BYTEA)
        self.assertEqual(actual["nullable"], PostgresValueType.UNKNOWN)

    def test_int_and_float_promote_deterministically_to_double_precision(self) -> None:
        dataset = Dataset([{"value": 1}, {"value": 2.5}], fields=("value",))
        self.assertEqual(
            self.mapper.plan(dataset).columns[0].value_type,
            PostgresValueType.DOUBLE_PRECISION,
        )

    def test_naive_and_aware_datetimes_are_not_mixed_silently(self) -> None:
        dataset = Dataset(
            [
                {"ts": datetime(2026, 9, 4, 12, 0)},
                {"ts": datetime(2026, 9, 4, 12, 0, tzinfo=UTC)},
            ]
        )
        with self.assertRaisesRegex(TargetConfigurationError, "incompatible"):
            self.mapper.plan(dataset)

    def test_nested_values_require_explicit_future_json_mapping(self) -> None:
        with self.assertRaisesRegex(TargetConfigurationError, "unsupported"):
            self.mapper.plan(Dataset([{"payload": {"nested": True}}]))

    def test_existing_table_validation_accepts_supported_compatible_types(self) -> None:
        table = Table(
            "demo",
            MetaData(),
            Column("text_value", Text),
            Column("int_value", BIGINT),
            Column("float_value", DOUBLE_PRECISION),
            Column("decimal_value", NUMERIC),
            Column("bool_value", BOOLEAN),
            Column("date_value", DATE),
            Column("naive_ts", TIMESTAMP(timezone=False)),
            Column("aware_ts", TIMESTAMP(timezone=True)),
            Column("bytes_value", LargeBinary),
            Column("nullable", Text),
        )
        dataset = Dataset(
            [
                {
                    "text_value": "x",
                    "int_value": 1,
                    "float_value": 1.25,
                    "decimal_value": Decimal("1.25"),
                    "bool_value": False,
                    "date_value": date(2026, 9, 4),
                    "naive_ts": datetime(2026, 9, 4, 10, 0),
                    "aware_ts": datetime(2026, 9, 4, 10, 0, tzinfo=UTC),
                    "bytes_value": b"x",
                    "nullable": None,
                }
            ]
        )
        self.mapper.validate_table(self.mapper.plan(dataset), table)

    def test_existing_table_validation_reports_type_mismatch_before_load(self) -> None:
        table = Table("demo", MetaData(), Column("name", BIGINT))
        with self.assertRaisesRegex(TargetConfigurationError, "schema mismatch"):
            self.mapper.validate_table(self.mapper.plan(Dataset([{"name": "wrong"}])), table)


if __name__ == "__main__":
    unittest.main()
