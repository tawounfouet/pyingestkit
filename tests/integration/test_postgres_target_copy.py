from __future__ import annotations

import os
import unittest
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine

from pyingestkit import Dataset
from pyingestkit.targets import PostgresTarget, TargetLoadError, TargetLoadRequest
from pyingestkit.targets.errors import TargetConfigurationError

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")


@unittest.skipUnless(POSTGRES_DSN, "PYINGEST_TEST_POSTGRES_DSN is required for PostgreSQL E2E")
class PostgresCopyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert POSTGRES_DSN is not None
        cls.engine = create_engine(POSTGRES_DSN, future=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE IF EXISTS pyingest_a2_copy")
            connection.exec_driver_sql(
                """
                CREATE TABLE pyingest_a2_copy (
                    id BIGINT PRIMARY KEY,
                    text_value TEXT NOT NULL,
                    int_value BIGINT NOT NULL,
                    float_value DOUBLE PRECISION NOT NULL,
                    decimal_value NUMERIC(38, 18) NOT NULL,
                    bool_value BOOLEAN NOT NULL,
                    date_value DATE NOT NULL,
                    naive_ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    aware_ts TIMESTAMPTZ NOT NULL,
                    bytes_value BYTEA NOT NULL,
                    nullable_value TEXT NULL
                )
                """
            )

    def tearDown(self) -> None:
        with self.engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE IF EXISTS pyingest_a2_copy")

    def _target(self) -> PostgresTarget:
        assert POSTGRES_DSN is not None
        return PostgresTarget(target_id="postgres.ci", dsn=POSTGRES_DSN, default_schema="public")

    def test_copy_preserves_supported_values_and_column_order(self) -> None:
        aware = datetime(2026, 9, 4, 18, 15, tzinfo=timezone(timedelta(hours=2)))
        dataset = Dataset(
            [
                {
                    "id": 1,
                    "text_value": "Unicode café — tab\t newline\n quote ' double \"",
                    "int_value": 9_223_372_036,
                    "float_value": 3.1415926535,
                    "decimal_value": Decimal("12345678901234567890.123456789012345678"),
                    "bool_value": True,
                    "date_value": date(2026, 9, 4),
                    "naive_ts": datetime(2026, 9, 4, 16, 15),
                    "aware_ts": aware,
                    "bytes_value": b"\x00\x01binary\xff",
                    "nullable_value": None,
                },
                {
                    "id": 2,
                    "text_value": "second row",
                    "int_value": -5,
                    "float_value": -0.25,
                    "decimal_value": Decimal("0.000000000000000001"),
                    "bool_value": False,
                    "date_value": date(2026, 1, 1),
                    "naive_ts": datetime(2026, 1, 1, 0, 0),
                    "aware_ts": datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
                    "bytes_value": b"payload",
                    "nullable_value": "present",
                },
            ]
        )
        target = self._target()
        try:
            result = target.load(
                TargetLoadRequest(
                    target_id=target.target_id,
                    dataset_id="demo.a2.copy",
                    run_id="run-copy",
                    dataset=dataset,
                    table="pyingest_a2_copy",
                )
            )
        finally:
            target.close()

        self.assertEqual(result.rows_loaded, 2)
        self.assertEqual(result.metrics["copy_rows"], 2)
        with self.engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT id, text_value, decimal_value, aware_ts, bytes_value, nullable_value "
                "FROM pyingest_a2_copy ORDER BY id"
            ).all()
        self.assertEqual(rows[0].text_value, dataset[0]["text_value"])
        self.assertEqual(rows[0].decimal_value, dataset[0]["decimal_value"])
        self.assertEqual(rows[0].aware_ts, aware)
        self.assertEqual(bytes(rows[0].bytes_value), dataset[0]["bytes_value"])
        self.assertIsNone(rows[0].nullable_value)

    def test_copy_constraint_failure_rolls_back_all_rows(self) -> None:
        dataset = Dataset([self._minimal_row(1, "first"), self._minimal_row(1, "duplicate")])
        target = self._target()
        try:
            with self.assertRaises(TargetLoadError):
                target.load(
                    TargetLoadRequest(
                        target_id=target.target_id,
                        dataset_id="demo.a2.rollback",
                        run_id="run-copy-rollback",
                        dataset=dataset,
                        table="pyingest_a2_copy",
                    )
                )
        finally:
            target.close()
        with self.engine.connect() as connection:
            count = connection.exec_driver_sql("SELECT COUNT(*) FROM pyingest_a2_copy").scalar_one()
        self.assertEqual(count, 0)

    def test_schema_mismatch_is_explicit_before_copy(self) -> None:
        target = self._target()
        try:
            with self.assertRaisesRegex(TargetConfigurationError, "schema mismatch"):
                target.load(
                    TargetLoadRequest(
                        target_id=target.target_id,
                        dataset_id="demo.a2.schema",
                        run_id="run-schema",
                        dataset=Dataset([{"id": "wrong-type"}], fields=("id",)),
                        table="pyingest_a2_copy",
                    )
                )
        finally:
            target.close()

    @staticmethod
    def _minimal_row(identifier: int, text: str) -> dict[str, object]:
        return {
            "id": identifier,
            "text_value": text,
            "int_value": 1,
            "float_value": 1.0,
            "decimal_value": Decimal("1.0"),
            "bool_value": True,
            "date_value": date(2026, 9, 4),
            "naive_ts": datetime(2026, 9, 4, 12, 0),
            "aware_ts": datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
            "bytes_value": b"x",
            "nullable_value": None,
        }


if __name__ == "__main__":
    unittest.main()
