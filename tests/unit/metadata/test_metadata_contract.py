from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import MemoryMetadataStore, SQLiteMetadataStore
from pyingestkit.runtime import Runner


class Echo(Step):
    def execute(self, context: RunContext, data):
        return data


class Demo(Job):
    id = "demo.metadata_contract"

    def pipeline(self) -> Pipeline:
        return Pipeline([Echo()])


def exercise(test: unittest.TestCase, store, workspace: Path) -> None:
    result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(Demo(), initial_data={"ok": True})
    test.assertTrue(result.succeeded)
    run = store.get_run(result.run_id[:8])
    test.assertEqual(run.status, "SUCCESS")
    test.assertEqual(run.job_id, "demo.metadata_contract")
    test.assertEqual(len(store.list_steps(result.run_id)), 1)
    test.assertGreaterEqual(len(store.list_events(result.run_id)), 4)
    test.assertEqual(len(store.list_runs(job_id="demo.metadata_contract")), 1)

    store.record_validation(
        result.run_id,
        rule="required-fields",
        severity="ERROR",
        status="PASSED",
        message="required fields present",
        metadata={"token": "super-secret", "rows": 1},
    )
    validations = store.list_validations(result.run_id)
    test.assertEqual(len(validations), 1)
    test.assertEqual(validations[0].metadata["token"], "***REDACTED***")

    published_at = datetime.now(timezone.utc)
    store.record_publication(
        result.run_id,
        dataset_id="demo.dataset",
        status="PUBLISHED",
        candidate_path="candidate/data.json",
        published_path="published/data.json",
        published_at=published_at,
    )
    publications = store.list_publications(result.run_id)
    test.assertEqual(len(publications), 1)
    test.assertEqual(publications[0].dataset_id, "demo.dataset")
    test.assertEqual(publications[0].status, "PUBLISHED")
    test.assertIsNotNone(publications[0].published_at)


class MetadataContractTests(unittest.TestCase):
    def test_memory_store_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exercise(self, MemoryMetadataStore(), Path(tmp) / "work")

    def test_sqlite_store_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            exercise(self, SQLiteMetadataStore(root / "state.sqlite3"), root / "work")


if __name__ == "__main__":
    unittest.main()
