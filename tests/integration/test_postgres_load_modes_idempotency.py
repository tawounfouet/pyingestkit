from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine

from pyingestkit import Dataset
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.metadata import PostgresMetadataStore
from pyingestkit.targets import (
    IdempotencyAction,
    LoadMode,
    PostgresTarget,
    TargetLoadError,
    TargetLoadExecutor,
    TargetLoadRequest,
    TargetLoadStatus,
)

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")


@unittest.skipUnless(POSTGRES_DSN, "PYINGEST_TEST_POSTGRES_DSN is required for PostgreSQL E2E")
class PostgresLoadModesIdempotencyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assert POSTGRES_DSN is not None
        cls.engine = create_engine(POSTGRES_DSN, future=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.table = "pyingest_b2_modes"
        with self.engine.begin() as connection:
            connection.exec_driver_sql(f"DROP TABLE IF EXISTS {self.table}")
            connection.exec_driver_sql(
                f"CREATE TABLE {self.table} (id BIGINT PRIMARY KEY, name TEXT NOT NULL)"
            )

    def tearDown(self) -> None:
        with self.engine.begin() as connection:
            connection.exec_driver_sql(f"DROP TABLE IF EXISTS {self.table}")

    def _target(self) -> PostgresTarget:
        assert POSTGRES_DSN is not None
        return PostgresTarget(target_id="postgres.ci.b2", dsn=POSTGRES_DSN, default_schema="public")

    def _request(
        self,
        *,
        run_id: str,
        dataset: Dataset,
        version: str,
        mode: LoadMode,
        dataset_id: str = "demo.b2.modes",
    ) -> TargetLoadRequest:
        return TargetLoadRequest(
            target_id="postgres.ci.b2",
            dataset_id=dataset_id,
            dataset_version_id=version,
            run_id=run_id,
            dataset=dataset,
            table=self.table,
            mode=mode,
        )

    def test_truncate_and_replace_are_atomic_content_replacements(self) -> None:
        with self.engine.begin() as connection:
            connection.exec_driver_sql(f"INSERT INTO {self.table} VALUES (99, 'old')")

        target = self._target()
        try:
            truncated = target.load(
                self._request(
                    run_id="run-truncate",
                    dataset=Dataset([{"id": 1, "name": "new"}], fields=("id", "name")),
                    version="v1",
                    mode=LoadMode.TRUNCATE_LOAD,
                )
            )
            self.assertIs(truncated.status, TargetLoadStatus.SUCCESS)
            with self.engine.connect() as connection:
                rows = connection.exec_driver_sql(
                    f"SELECT id, name FROM {self.table} ORDER BY id"
                ).all()
            self.assertEqual(rows, [(1, "new")])

            replaced = target.load(
                self._request(
                    run_id="run-replace",
                    dataset=Dataset([{"id": 2, "name": "replacement"}], fields=("id", "name")),
                    version="v2",
                    mode=LoadMode.REPLACE,
                )
            )
            self.assertEqual(replaced.metrics["rows_deleted"], 1)
            with self.engine.connect() as connection:
                rows = connection.exec_driver_sql(
                    f"SELECT id, name FROM {self.table} ORDER BY id"
                ).all()
            self.assertEqual(rows, [(2, "replacement")])

            for mode in (LoadMode.TRUNCATE_LOAD, LoadMode.REPLACE):
                with self.subTest(mode=mode):
                    with self.assertRaises(TargetLoadError):
                        target.load(
                            self._request(
                                run_id=f"run-rollback-{mode.value}",
                                dataset=Dataset(
                                    [
                                        {"id": 3, "name": "first"},
                                        {"id": 3, "name": "duplicate"},
                                    ],
                                    fields=("id", "name"),
                                ),
                                version=f"rollback-{mode.value}",
                                mode=mode,
                            )
                        )
                    with self.engine.connect() as connection:
                        rows = connection.exec_driver_sql(
                            f"SELECT id, name FROM {self.table} ORDER BY id"
                        ).all()
                    self.assertEqual(rows, [(2, "replacement")])
        finally:
            target.close()

    def test_target_load_history_drives_skip_reload_and_retry(self) -> None:
        assert POSTGRES_DSN is not None
        store = PostgresMetadataStore(POSTGRES_DSN)
        target = self._target()
        executor = TargetLoadExecutor(target=target, metadata_store=store)
        dataset_id = f"demo.b2.idempotency.{uuid4()}"

        with tempfile.TemporaryDirectory() as tmp:
            artifact_store = LocalArtifactStore(Path(tmp) / "artifacts")

            def new_run() -> str:
                context = RunContext(
                    job_id="demo.postgres.b2",
                    job_version="0.5.0b2",
                    artifact_store=artifact_store,
                )
                store.start_run(context)
                return str(context.run_id)

            v1 = Dataset([{"id": 1, "name": "alpha"}], fields=("id", "name"))
            first = executor.execute(
                self._request(
                    run_id=new_run(),
                    dataset=v1,
                    version="version-1",
                    mode=LoadMode.APPEND,
                    dataset_id=dataset_id,
                )
            )
            self.assertIs(first.idempotency_action, IdempotencyAction.EXECUTE)

            duplicate = executor.execute(
                self._request(
                    run_id=new_run(),
                    dataset=v1,
                    version="version-1",
                    mode=LoadMode.APPEND,
                    dataset_id=dataset_id,
                )
            )
            self.assertIs(duplicate.status, TargetLoadStatus.SKIPPED)
            self.assertIs(duplicate.idempotency_action, IdempotencyAction.SKIP)
            with self.engine.connect() as connection:
                self.assertEqual(
                    connection.exec_driver_sql(f"SELECT COUNT(*) FROM {self.table}").scalar_one(),
                    1,
                )

            v2 = Dataset([{"id": 2, "name": "beta"}], fields=("id", "name"))
            reloaded = executor.execute(
                self._request(
                    run_id=new_run(),
                    dataset=v2,
                    version="version-2",
                    mode=LoadMode.TRUNCATE_LOAD,
                    dataset_id=dataset_id,
                )
            )
            self.assertIs(reloaded.idempotency_action, IdempotencyAction.RELOAD)
            with self.engine.connect() as connection:
                rows = connection.exec_driver_sql(
                    f"SELECT id, name FROM {self.table} ORDER BY id"
                ).all()
            self.assertEqual(rows, [(2, "beta")])

            duplicate_reload = executor.execute(
                self._request(
                    run_id=new_run(),
                    dataset=v2,
                    version="version-2",
                    mode=LoadMode.TRUNCATE_LOAD,
                    dataset_id=dataset_id,
                )
            )
            self.assertIs(duplicate_reload.idempotency_action, IdempotencyAction.SKIP)

            conflicting = Dataset([{"id": 2, "name": "conflict"}], fields=("id", "name"))
            failed_run_id = new_run()
            with self.assertRaises(TargetLoadError):
                executor.execute(
                    self._request(
                        run_id=failed_run_id,
                        dataset=conflicting,
                        version="version-3",
                        mode=LoadMode.APPEND,
                        dataset_id=dataset_id,
                    )
                )
            failed_records = store.list_target_loads(run_id=failed_run_id)
            self.assertEqual(len(failed_records), 1)
            self.assertEqual(failed_records[0].status, "ROLLED_BACK")

            # Simulate the transient destination conflict being resolved without changing
            # the Dataset/version identity; the next decision must be RETRY, not EXECUTE.
            with self.engine.begin() as connection:
                connection.exec_driver_sql(f"TRUNCATE TABLE {self.table}")
            retried = executor.execute(
                self._request(
                    run_id=new_run(),
                    dataset=conflicting,
                    version="version-3",
                    mode=LoadMode.APPEND,
                    dataset_id=dataset_id,
                )
            )
            self.assertIs(retried.idempotency_action, IdempotencyAction.RETRY)

            exact = store.list_target_loads(
                dataset_id=dataset_id,
                target_id=target.target_id,
                dataset_version_id="version-3",
                destination=f"public.{self.table}",
                mode="append",
            )
            self.assertGreaterEqual(len(exact), 2)
            self.assertEqual(exact[0].status, "SUCCESS")
            self.assertEqual(exact[0].idempotency_action, "retry")
        target.close()


if __name__ == "__main__":
    unittest.main()
