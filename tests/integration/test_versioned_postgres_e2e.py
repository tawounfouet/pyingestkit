from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from pyingestkit_demo_jobs.versioned_postgres import (
    DATASET_ID,
    REVISION_2,
    job_definition,
)
from sqlalchemy import create_engine

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.registry import JobRegistry
from pyingestkit.metadata import (
    PostgresMetadataStore,
    SQLiteMetadataStore,
    TargetLoadMetadataCapability,
)
from pyingestkit.replay import ReplayService
from pyingestkit.runtime import Runner
from pyingestkit.targets import IdempotencyAction, TargetLoadStatus
from pyingestkit.versioning import FilesystemDatasetVersionStore

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")


@unittest.skipUnless(POSTGRES_DSN, "PYINGEST_TEST_POSTGRES_DSN is required")
class VersionedPostgresE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        assert POSTGRES_DSN is not None
        self.dsn = POSTGRES_DSN
        self.engine = create_engine(self.dsn, future=True)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _prepare_target(self, table: str) -> None:
        with self.engine.begin() as connection:
            connection.exec_driver_sql(f'DROP TABLE IF EXISTS "{table}"')
            connection.exec_driver_sql(
                f'CREATE TABLE "{table}" ('
                "id BIGINT PRIMARY KEY, "
                "name TEXT NOT NULL, "
                "score DOUBLE PRECISION NOT NULL)"
            )

    def _rows(self, table: str) -> list[tuple[int, str, float]]:
        with self.engine.connect() as connection:
            rows = connection.exec_driver_sql(
                f'SELECT id, name, score FROM "{table}" ORDER BY id'
            ).all()
        return [(int(row[0]), str(row[1]), float(row[2])) for row in rows]

    def _exercise(self, *, metadata_backend: str) -> None:
        suffix = uuid4().hex[:10]
        table = f"pyingestkit_rc1_{metadata_backend}_{suffix}"
        target_id = f"postgres.rc1.{metadata_backend}.{suffix}"
        self._prepare_target(table)

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            if metadata_backend == "sqlite":
                metadata = SQLiteMetadataStore(workspace / "state" / "pyingest.sqlite3")
            else:
                metadata = PostgresMetadataStore(self.dsn)
            self.assertIsInstance(metadata, TargetLoadMetadataCapability)

            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            job = job_definition.build()
            parameters = {
                "revision": 1,
                "target_id": target_id,
                "target_table": table,
                "target_schema": "public",
                "target_dsn_env": "PYINGEST_TARGET_DATABASE_URL",
                "metadata_backend": metadata_backend,
                "metadata_dsn_env": "PYINGEST_DATABASE_URL",
            }
            old_target_dsn = os.environ.get("PYINGEST_TARGET_DATABASE_URL")
            old_metadata_dsn = os.environ.get("PYINGEST_DATABASE_URL")
            os.environ["PYINGEST_TARGET_DATABASE_URL"] = self.dsn
            os.environ["PYINGEST_DATABASE_URL"] = self.dsn
            try:
                first = runner.run(job, parameters=parameters, fixture_mode=True)
                self.assertTrue(first.succeeded, first.error)
                first_loads = metadata.list_target_loads(run_id=first.run_id)
                self.assertEqual(len(first_loads), 1)
                self.assertEqual(first_loads[0].status, TargetLoadStatus.SUCCESS.value)
                self.assertEqual(first_loads[0].idempotency_action, IdempotencyAction.EXECUTE.value)
                self.assertEqual(
                    self._rows(table),
                    [(1, "Alice", 91.5), (2, "Bob", 87.0), (4, "Dora", 70.0)],
                )

                parameters["revision"] = 2
                second = runner.run(job, parameters=parameters, fixture_mode=True)
                self.assertTrue(second.succeeded, second.error)
                second_loads = metadata.list_target_loads(run_id=second.run_id)
                self.assertEqual(len(second_loads), 1)
                self.assertEqual(second_loads[0].status, TargetLoadStatus.SUCCESS.value)
                self.assertEqual(second_loads[0].idempotency_action, IdempotencyAction.RELOAD.value)
                self.assertEqual(
                    self._rows(table),
                    [(1, "Alice", 92.0), (2, "Bob", 87.0), (3, "Carla", 80.0)],
                )
                versions = FilesystemDatasetVersionStore(workspace, metadata_store=metadata)
                all_versions = versions.list_versions(DATASET_ID)
                self.assertEqual(len(all_versions), 2)
                published = versions.get_published(DATASET_ID)
                self.assertIsNotNone(published)
                assert published is not None
                self.assertEqual(published.published_from_run_id, second.run_id)

                diff_path = runner.artifact_store.path_for(
                    DATASET_ID, UUID(second.run_id), "reports/diff.json"
                )
                diff = json.loads(diff_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    diff["summary"],
                    {"added": 1, "removed": 1, "changed": 1, "unchanged": 1},
                )

                registry = JobRegistry()
                registry.register(job)
                replay = ReplayService(runner, registry).replay(second.run_id)
                self.assertTrue(replay.succeeded)
                self.assertEqual(replay.verification_mode, "STRICT")
                self.assertTrue(replay.matched)
                self.assertEqual(replay.expected_fingerprint, published.fingerprint.id)
                self.assertEqual(replay.actual_fingerprint, published.fingerprint.id)

                replay_loads = metadata.list_target_loads(run_id=replay.run.run_id)
                self.assertEqual(len(replay_loads), 1)
                self.assertEqual(replay_loads[0].status, TargetLoadStatus.SKIPPED.value)
                self.assertEqual(replay_loads[0].idempotency_action, IdempotencyAction.SKIP.value)
                self.assertEqual(replay_loads[0].rows_loaded, 0)
                self.assertEqual(
                    self._rows(table),
                    [(1, "Alice", 92.0), (2, "Bob", 87.0), (3, "Carla", 80.0)],
                )
                still_published = versions.get_published(DATASET_ID)
                self.assertIsNotNone(still_published)
                assert still_published is not None
                self.assertEqual(still_published.version_id, published.version_id)
                self.assertEqual(still_published.published_from_run_id, second.run_id)

                source_raw = metadata.list_artifacts(second.run_id)
                replay_raw = metadata.list_artifacts(replay.run.run_id)
                self.assertEqual(len(source_raw), 1)
                self.assertEqual(len(replay_raw), 1)
                self.assertEqual(source_raw[0].sha256, replay_raw[0].sha256)
                self.assertEqual(Path(replay_raw[0].path).read_bytes(), REVISION_2)
                replay_events = metadata.list_events(replay.run.run_id)
                self.assertTrue(any(event.event_type == "RAW_REPLAYED" for event in replay_events))
            finally:
                if old_target_dsn is None:
                    os.environ.pop("PYINGEST_TARGET_DATABASE_URL", None)
                else:
                    os.environ["PYINGEST_TARGET_DATABASE_URL"] = old_target_dsn
                if old_metadata_dsn is None:
                    os.environ.pop("PYINGEST_DATABASE_URL", None)
                else:
                    os.environ["PYINGEST_DATABASE_URL"] = old_metadata_dsn

    def test_sqlite_metadata_plus_postgres_target_full_slice(self) -> None:
        self._exercise(metadata_backend="sqlite")

    def test_postgres_metadata_plus_postgres_target_full_slice(self) -> None:
        self._exercise(metadata_backend="postgres")


if __name__ == "__main__":
    unittest.main()
