from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from pyingestkit_demo_jobs.versioned_ndjson import job_definition

from pyingestkit.artifacts import S3ArtifactStore
from pyingestkit.core.registry import JobRegistry
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.replay import ReplayService
from pyingestkit.runtime import Runner

ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")


@unittest.skipUnless(ENDPOINT and BUCKET, "S3-compatible endpoint and bucket are required")
class S3RemoteRawIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import boto3

        assert ENDPOINT is not None
        assert BUCKET is not None
        cls.client = boto3.client("s3", endpoint_url=ENDPOINT, region_name="us-east-1")
        try:
            cls.client.create_bucket(Bucket=BUCKET)
        except cls.client.exceptions.BucketAlreadyOwnedByYou:
            pass

    def test_remote_raw_survives_local_cache_loss_and_strict_replay(self) -> None:
        assert ENDPOINT is not None
        assert BUCKET is not None
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            prefix = f"a2/{uuid4().hex}"
            artifact_store = S3ArtifactStore(
                bucket=BUCKET,
                prefix=prefix,
                cache_root=workspace,
                endpoint_url=ENDPOINT,
                region_name="us-east-1",
            )
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            runner = Runner(artifact_store, metadata_store=metadata)
            job = job_definition.build()

            first = runner.run(job, parameters={"revision": 1}, fixture_mode=True)
            self.assertTrue(first.succeeded, first.error)
            records = metadata.list_artifacts(first.run_id)
            self.assertEqual(len(records), 1)
            source = records[0]
            self.assertIsNotNone(source.storage_uri)
            assert source.storage_uri is not None
            self.assertTrue(source.storage_uri.startswith(f"s3://{BUCKET}/{prefix}/runs/"))

            remote = self.client.head_object(
                Bucket=BUCKET,
                Key=source.storage_uri.split(f"s3://{BUCKET}/", 1)[1],
            )
            self.assertEqual(remote["Metadata"]["pyingestkit-sha256"], source.sha256)

            source_cache = Path(source.path)
            source_cache.unlink()
            self.assertFalse(source_cache.exists())

            registry = JobRegistry()
            registry.register(job)
            replay = ReplayService(runner, registry).replay(first.run_id)
            self.assertTrue(replay.succeeded)
            self.assertTrue(replay.matched)
            self.assertEqual(replay.verification_mode, "STRICT")

            replay_records = metadata.list_artifacts(replay.run.run_id)
            self.assertEqual(len(replay_records), 1)
            replay_raw = replay_records[0]
            self.assertIsNotNone(replay_raw.storage_uri)
            self.assertEqual(replay_raw.sha256, source.sha256)
            self.assertTrue(Path(replay_raw.path).is_file())
            self.assertNotEqual(replay_raw.storage_uri, source.storage_uri)


if __name__ == "__main__":
    unittest.main()
