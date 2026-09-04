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
    TargetConfigurationError,
    TargetLoadError,
    TargetLoadRequest,
    TargetLoadStatus,
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

    def test_b2_capabilities_enable_all_three_content_load_modes(self) -> None:
        engine = _sqlite_engine()
        target = self._target(engine)
        self.assertTrue(target.capabilities.transactional)
        self.assertTrue(target.capabilities.bulk_load)
        self.assertTrue(target.capabilities.append)
        self.assertTrue(target.capabilities.truncate_load)
        self.assertTrue(target.capabilities.replace)
        self.assertFalse(target.capabilities.upsert)
        self.assertFalse(target.capabilities.staging)

    def test_truncate_load_replaces_contents_in_one_transaction(self) -> None:
        engine = _sqlite_engine()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE demo_dataset (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.exec_driver_sql("INSERT INTO demo_dataset VALUES (99, 'old')")
        target = self._target(engine)
        result = target.load(
            TargetLoadRequest(
                target_id=target.target_id,
                dataset_id="demo.dataset",
                run_id="run-truncate",
                dataset=Dataset([{"id": 1, "name": "new"}], fields=("id", "name")),
                table="demo_dataset",
                mode=LoadMode.TRUNCATE_LOAD,
            )
        )
        self.assertIs(result.status, TargetLoadStatus.SUCCESS)
        self.assertEqual(result.metrics["content_reset"], 1)
        with engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT id, name FROM demo_dataset ORDER BY id"
            ).all()
        self.assertEqual(rows, [(1, "new")])

    def test_replace_uses_delete_semantics_and_reports_deleted_rows(self) -> None:
        engine = _sqlite_engine()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE demo_dataset (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.exec_driver_sql("INSERT INTO demo_dataset VALUES (99, 'old')")
        target = self._target(engine)
        result = target.load(
            TargetLoadRequest(
                target_id=target.target_id,
                dataset_id="demo.dataset",
                run_id="run-replace",
                dataset=Dataset([{"id": 2, "name": "replacement"}], fields=("id", "name")),
                table="demo_dataset",
                mode=LoadMode.REPLACE,
            )
        )
        self.assertEqual(result.metrics["rows_deleted"], 1)
        with engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT id, name FROM demo_dataset ORDER BY id"
            ).all()
        self.assertEqual(rows, [(2, "replacement")])

    def test_destructive_modes_roll_back_to_prior_contents_on_failure(self) -> None:
        for mode in (LoadMode.TRUNCATE_LOAD, LoadMode.REPLACE):
            with self.subTest(mode=mode):
                engine = _sqlite_engine()
                with engine.begin() as connection:
                    connection.exec_driver_sql(
                        "CREATE TABLE demo_dataset (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
                    )
                    connection.exec_driver_sql("INSERT INTO demo_dataset VALUES (99, 'old')")
                target = self._target(engine)
                with self.assertRaises(TargetLoadError):
                    target.load(
                        TargetLoadRequest(
                            target_id=target.target_id,
                            dataset_id="demo.dataset",
                            run_id=f"run-{mode.value}",
                            dataset=Dataset(
                                [
                                    {"id": 1, "name": "first"},
                                    {"id": 1, "name": "duplicate"},
                                ],
                                fields=("id", "name"),
                            ),
                            table="demo_dataset",
                            mode=mode,
                        )
                    )
                with engine.connect() as connection:
                    rows = connection.exec_driver_sql(
                        "SELECT id, name FROM demo_dataset ORDER BY id"
                    ).all()
                self.assertEqual(rows, [(99, "old")])

    def test_expected_row_count_is_checked_before_mutation(self) -> None:
        engine = _sqlite_engine()
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE demo_dataset (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
            connection.exec_driver_sql("INSERT INTO demo_dataset VALUES (99, 'old')")
        target = self._target(engine)
        with self.assertRaisesRegex(TargetConfigurationError, "expected_row_count mismatch"):
            target.load(
                TargetLoadRequest(
                    target_id=target.target_id,
                    dataset_id="demo.dataset",
                    run_id="run-expected",
                    dataset=Dataset([{"id": 1, "name": "new"}], fields=("id", "name")),
                    table="demo_dataset",
                    mode=LoadMode.TRUNCATE_LOAD,
                    expected_row_count=2,
                )
            )
        with engine.connect() as connection:
            rows = connection.exec_driver_sql(
                "SELECT id, name FROM demo_dataset ORDER BY id"
            ).all()
        self.assertEqual(rows, [(99, "old")])



if __name__ == "__main__":
    unittest.main()
