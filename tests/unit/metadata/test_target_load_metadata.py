from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.metadata import (
    MemoryMetadataStore,
    MetadataStore,
    SQLiteMetadataStore,
    TargetLoadMetadataCapability,
    TargetLoadRecord,
)
from pyingestkit.targets import LoadMode, TargetLoadResult, TargetLoadStatus


class TargetLoadMetadataTests(unittest.TestCase):
    def test_capability_is_additive_and_does_not_change_base_store_contract(self) -> None:
        self.assertNotIn("record_target_load", MetadataStore.__abstractmethods__)
        self.assertIsInstance(MemoryMetadataStore(), TargetLoadMetadataCapability)

    def test_record_can_be_built_from_target_result(self) -> None:
        started = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
        completed = started + timedelta(seconds=2)
        result = TargetLoadResult(
            load_id="load-1",
            target_id="postgres.demo",
            dataset_id="demo.dataset",
            dataset_version_id="sha256-abc",
            run_id="run-1",
            mode=LoadMode.APPEND,
            status=TargetLoadStatus.SUCCESS,
            rows_input=10,
            rows_loaded=10,
            rows_verified=None,
            started_at=started,
            completed_at=completed,
            duration_seconds=2.0,
            destination="public.demo",
            metrics={"copy_rows": 10},
        )
        record = TargetLoadRecord.from_result(result)
        self.assertEqual(record.load_id, result.load_id)
        self.assertEqual(record.status, "SUCCESS")
        self.assertEqual(record.mode, "append")
        self.assertEqual(record.metrics["copy_rows"], 10)

    def test_memory_store_upserts_same_load_and_filters(self) -> None:
        store = MemoryMetadataStore()
        created = datetime(2026, 9, 4, 20, 0, tzinfo=UTC)
        running = self._record(
            load_id="load-memory",
            run_id="run-memory",
            status="RUNNING",
            completed_at=None,
            duration_seconds=None,
            rows_loaded=0,
            created_at=created,
        )
        store.record_target_load(running)
        store.record_target_load(
            replace(
                running,
                status="SUCCESS",
                completed_at=created + timedelta(seconds=1),
                duration_seconds=1.0,
                rows_loaded=3,
                error="password=super-secret",
                created_at=created + timedelta(seconds=5),
            )
        )

        stored = store.get_target_load("load-memory")
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.status, "SUCCESS")
        self.assertEqual(stored.rows_loaded, 3)
        self.assertEqual(stored.created_at, created)
        self.assertNotIn("super-secret", stored.error or "")
        self.assertEqual(
            len(store.list_target_loads(run_id="run-memory", status="success")),
            1,
        )

    def test_sqlite_schema_and_foreign_key_backed_recording(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SQLiteMetadataStore.for_workspace(root)
            context = RunContext(
                job_id="demo.metadata",
                job_version="0.5.0b1",
                artifact_store=LocalArtifactStore(root / "artifacts"),
            )
            store.start_run(context)
            record = self._record(
                load_id="load-sqlite",
                run_id=str(context.run_id),
                status="SUCCESS",
                completed_at=datetime(2026, 9, 4, 20, 0, 1, tzinfo=UTC),
                duration_seconds=1.0,
                rows_loaded=3,
                created_at=datetime(2026, 9, 4, 20, 0, tzinfo=UTC),
            )
            store.record_target_load(record)

            stored = store.get_target_load(record.load_id)
            self.assertEqual(stored, record)
            self.assertEqual(
                store.list_target_loads(dataset_id="demo.dataset", target_id="postgres.demo"),
                (record,),
            )

    @staticmethod
    def _record(
        *,
        load_id: str,
        run_id: str,
        status: str,
        completed_at: datetime | None,
        duration_seconds: float | None,
        rows_loaded: int,
        created_at: datetime,
    ) -> TargetLoadRecord:
        return TargetLoadRecord(
            load_id=load_id,
            run_id=run_id,
            target_id="postgres.demo",
            dataset_id="demo.dataset",
            dataset_version_id="sha256-abc",
            mode="append",
            status=status,
            destination="public.demo_dataset",
            rows_input=3,
            rows_loaded=rows_loaded,
            rows_verified=None,
            started_at=datetime(2026, 9, 4, 20, 0, tzinfo=UTC),
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            idempotency_action=None,
            metrics={"copy_rows": rows_loaded},
            error=None,
            created_at=created_at,
        )


if __name__ == "__main__":
    unittest.main()
