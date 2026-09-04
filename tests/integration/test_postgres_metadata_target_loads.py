from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.metadata import PostgresMetadataStore, TargetLoadRecord

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")


@unittest.skipUnless(POSTGRES_DSN, "PYINGEST_TEST_POSTGRES_DSN is required for PostgreSQL E2E")
class PostgresTargetLoadMetadataIntegrationTests(unittest.TestCase):
    def test_postgres_store_persists_and_updates_target_load_lineage(self) -> None:
        assert POSTGRES_DSN is not None
        store = PostgresMetadataStore(POSTGRES_DSN)
        self.assertNotIn("postgres:postgres@", store.safe_dsn)

        with tempfile.TemporaryDirectory() as tmp:
            context = RunContext(
                job_id="demo.postgres.metadata",
                job_version="0.5.0b1",
                artifact_store=LocalArtifactStore(Path(tmp) / "artifacts"),
            )
            store.start_run(context)
            run_id = str(context.run_id)
            created = datetime.now(UTC)
            record = TargetLoadRecord(
                load_id=f"load-{uuid4()}",
                run_id=run_id,
                target_id="postgres.ci",
                dataset_id="demo.postgres.metadata",
                dataset_version_id="sha256-" + "a" * 64,
                mode="append",
                status="RUNNING",
                destination="public.pyingest_b1_metadata",
                rows_input=2,
                rows_loaded=0,
                rows_verified=None,
                started_at=created,
                completed_at=None,
                duration_seconds=None,
                idempotency_action=None,
                metrics={},
                error=None,
                created_at=created,
            )
            store.record_target_load(record)
            completed = replace(
                record,
                status="SUCCESS",
                rows_loaded=2,
                completed_at=created + timedelta(milliseconds=10),
                duration_seconds=0.01,
                metrics={"copy_rows": 2},
            )
            store.record_target_load(completed)

            loaded = store.get_target_load(record.load_id)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.status, "SUCCESS")
            self.assertEqual(loaded.rows_loaded, 2)
            self.assertEqual(loaded.created_at, created)
            rows = store.list_target_loads(
                run_id=run_id,
                dataset_id="demo.postgres.metadata",
                target_id="postgres.ci",
                status="success",
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].load_id, record.load_id)


if __name__ == "__main__":
    unittest.main()
