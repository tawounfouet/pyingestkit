from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from pyingestkit import Dataset
from pyingestkit.targets import (
    InvalidTargetIdentifierError,
    LoadMode,
    PostgresTarget,
    TargetClosedError,
    TargetLoadError,
    TargetLoadRequest,
    TargetLoadStatus,
    UnsupportedLoadModeError,
)


def _sqlite_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


class PostgresTargetTests(unittest.TestCase):
    def _target(self, engine):
        patcher = patch.object(PostgresTarget, "_create_engine", return_value=engine)
        patcher.start()
        self.addCleanup(patcher.stop)
        return PostgresTarget(
            target_id="postgres.demo",
            dsn="postgresql://demo:very-secret@db.example/app",
            default_schema=None,
        )

    def test_dsn_normalization_and_redaction(self) -> None:
        engine = _sqlite_engine()
        target = self._target(engine)
        self.assertNotIn("very-secret", target.safe_dsn)
        self.assertIn("***", target.safe_dsn)
        target.close()

    def test_open_and_close_are_safe_and_close_is_idempotent(self) -> None:
        engine = _sqlite_engine()
        target = self._target(engine)
        self.assertIs(target.open(), target)
        target.close()
        target.close()
        self.assertTrue(target.closed)
        with self.assertRaises(TargetClosedError):
            target.open()

    def test_append_uses_one_transaction_and_returns_structured_result(self) -> None:
        engine = _sqlite_engine()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE demo_dataset (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        target = self._target(engine)
        dataset = Dataset(
            [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}],
            fields=("id", "name"),
        )
        result = target.load(
            TargetLoadRequest(
                target_id=target.target_id,
                dataset_id="demo.dataset",
                run_id="run-1",
                dataset=dataset,
                table="demo_dataset",
                mode=LoadMode.APPEND,
            )
        )
        self.assertIs(result.status, TargetLoadStatus.SUCCESS)
        self.assertEqual(result.rows_input, 2)
        self.assertEqual(result.rows_loaded, 2)
        self.assertEqual(result.destination, "demo_dataset")
        with engine.connect() as connection:
            count = connection.exec_driver_sql("SELECT COUNT(*) FROM demo_dataset").scalar_one()
        self.assertEqual(count, 2)

    def test_database_failure_rolls_back_the_whole_load(self) -> None:
        engine = _sqlite_engine()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE demo_dataset (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.exec_driver_sql("INSERT INTO demo_dataset(id, name) VALUES (1, 'existing')")
        target = self._target(engine)
        dataset = Dataset(
            [{"id": 2, "name": "first"}, {"id": 2, "name": "duplicate"}],
            fields=("id", "name"),
        )
        with self.assertRaises(TargetLoadError):
            target.load(
                TargetLoadRequest(
                    target_id=target.target_id,
                    dataset_id="demo.dataset",
                    run_id="run-rollback",
                    dataset=dataset,
                    table="demo_dataset",
                )
            )
        with engine.connect() as connection:
            result = connection.exec_driver_sql("SELECT id FROM demo_dataset ORDER BY id")
            ids = result.scalars().all()
        self.assertEqual(ids, [1])

    def test_identifier_policy_rejects_sql_fragments(self) -> None:
        engine = _sqlite_engine()
        target = self._target(engine)
        dataset = Dataset([{"id": 1}], fields=("id",))
        with self.assertRaises(InvalidTargetIdentifierError):
            target.load(
                TargetLoadRequest(
                    target_id=target.target_id,
                    dataset_id="demo.dataset",
                    run_id="run-1",
                    dataset=dataset,
                    table="demo; DROP TABLE users",
                )
            )

    def test_a1_rejects_future_load_modes_explicitly(self) -> None:
        engine = _sqlite_engine()
        target = self._target(engine)
        dataset = Dataset([], fields=("id",))
        with self.assertRaises(UnsupportedLoadModeError):
            target.load(
                TargetLoadRequest(
                    target_id=target.target_id,
                    dataset_id="demo.dataset",
                    run_id="run-1",
                    dataset=dataset,
                    table="demo_dataset",
                    mode=LoadMode.REPLACE,
                )
            )


if __name__ == "__main__":
    unittest.main()
