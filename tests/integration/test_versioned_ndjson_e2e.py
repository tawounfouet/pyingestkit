from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.registry import JobRegistry
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.replay import ReplayService
from pyingestkit.runtime import Runner
from pyingestkit.versioning import FilesystemDatasetVersionStore
from pyingestkit_demo_jobs.versioned_ndjson import DATASET_ID, job_definition


class VersionedNdjsonE2ETests(unittest.TestCase):
    def test_v1_v2_diff_publish_and_strict_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            metadata = SQLiteMetadataStore(workspace / "state" / "pyingest.sqlite3")
            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            job = job_definition.build()

            first = runner.run(job, parameters={"revision": 1}, fixture_mode=True)
            self.assertTrue(first.succeeded)

            versions = FilesystemDatasetVersionStore(workspace)
            first_versions = versions.list_versions(DATASET_ID)
            self.assertEqual(len(first_versions), 1)
            first_published = versions.get_published(DATASET_ID)
            self.assertIsNotNone(first_published)

            second = runner.run(job, parameters={"revision": 2}, fixture_mode=True)
            self.assertTrue(second.succeeded)

            all_versions = versions.list_versions(DATASET_ID)
            self.assertEqual(len(all_versions), 2)
            second_published = versions.get_published(DATASET_ID)
            self.assertIsNotNone(second_published)
            assert first_published is not None
            assert second_published is not None
            self.assertNotEqual(first_published.version_id, second_published.version_id)
            self.assertEqual(second_published.published_from_run_id, second.run_id)

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

            self.assertTrue(replay.run.succeeded)
            self.assertEqual(replay.verification_mode, "STRICT")
            self.assertTrue(replay.matched)
            self.assertEqual(replay.expected_fingerprint, second_published.fingerprint.id)
            self.assertEqual(replay.actual_fingerprint, second_published.fingerprint.id)

            source_raw = metadata.list_artifacts(second.run_id)
            replay_raw = metadata.list_artifacts(replay.run.run_id)
            self.assertEqual(len(source_raw), 1)
            self.assertEqual(len(replay_raw), 1)
            self.assertEqual(source_raw[0].sha256, replay_raw[0].sha256)


if __name__ == "__main__":
    unittest.main()
