from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from pyingestkit_demo_jobs.versioned_s3 import DATASET_ID, REVISION_2, job_definition
from sqlalchemy import MetaData, Table, create_engine, select

from pyingestkit.artifacts import S3ArtifactStore
from pyingestkit.core.registry import JobRegistry
from pyingestkit.metadata import PostgresMetadataStore
from pyingestkit.replay import ReplayService
from pyingestkit.runtime import Runner
from pyingestkit.targets import IdempotencyAction, TargetLoadStatus
from pyingestkit.versioning import S3DatasetVersionStore

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")
ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")


@unittest.skipUnless(
    POSTGRES_DSN and ENDPOINT and BUCKET,
    "PostgreSQL and S3-compatible service are required",
)
class VersionedS3CrossHostE2ETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import boto3

        assert POSTGRES_DSN is not None
        assert ENDPOINT is not None
        assert BUCKET is not None
        cls.dsn = POSTGRES_DSN
        cls.client = boto3.client("s3", endpoint_url=ENDPOINT, region_name="us-east-1")
        try:
            cls.client.create_bucket(Bucket=BUCKET)
        except cls.client.exceptions.BucketAlreadyOwnedByYou:
            pass

    def setUp(self) -> None:
        self.engine = create_engine(self.dsn, future=True)

    def tearDown(self) -> None:
        self.engine.dispose()

    def _drop_target(self, table: str) -> None:
        with self.engine.begin() as connection:
            Table(table, MetaData(), schema="public").drop(connection, checkfirst=True)

    def _rows(self, table: str) -> list[tuple[int, str, float]]:
        with self.engine.connect() as connection:
            destination = Table(
                table,
                MetaData(),
                schema="public",
                autoload_with=connection,
            )
            rows = connection.execute(
                select(destination.c.id, destination.c.name, destination.c.score).order_by(
                    destination.c.id
                )
            ).all()
        return [(int(row[0]), str(row[1]), float(row[2])) for row in rows]

    def test_full_remote_v1_v2_destroy_workspace_and_replay_from_fresh_runner(self) -> None:
        assert ENDPOINT is not None
        assert BUCKET is not None
        suffix = uuid4().hex[:10]
        prefix = f"rc1/{suffix}"
        table = f"pyingestkit_rc1_s3_{suffix}"
        target_id = f"postgres.rc1.s3.{suffix}"
        self._drop_target(table)

        old_target_dsn = os.environ.get("PYINGEST_TARGET_DATABASE_URL")
        old_metadata_dsn = os.environ.get("PYINGEST_DATABASE_URL")
        os.environ["PYINGEST_TARGET_DATABASE_URL"] = self.dsn
        os.environ["PYINGEST_DATABASE_URL"] = self.dsn
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                workspace_a = root / "host-a" / ".pyingest"
                workspace_b = root / "host-b" / ".pyingest"

                metadata_a = PostgresMetadataStore(self.dsn)
                metadata_a.initialize()
                artifacts_a = S3ArtifactStore(
                    bucket=BUCKET,
                    prefix=prefix,
                    cache_root=workspace_a,
                    endpoint_url=ENDPOINT,
                    region_name="us-east-1",
                )
                runner_a = Runner(artifacts_a, metadata_store=metadata_a)
                job = job_definition.build()
                parameters = {
                    "revision": 1,
                    "target_id": target_id,
                    "target_table": table,
                    "target_schema": "public",
                    "target_dsn_env": "PYINGEST_TARGET_DATABASE_URL",
                    "metadata_dsn_env": "PYINGEST_DATABASE_URL",
                }

                first = runner_a.run(job, parameters=parameters, fixture_mode=True)
                self.assertTrue(first.succeeded, first.error)
                first_load = metadata_a.list_target_loads(run_id=first.run_id)
                self.assertEqual(len(first_load), 1)
                self.assertEqual(first_load[0].status, TargetLoadStatus.SUCCESS.value)
                self.assertEqual(first_load[0].idempotency_action, IdempotencyAction.EXECUTE.value)
                self.assertEqual(
                    self._rows(table),
                    [(1, "Alice", 91.5), (2, "Bob", 87.0), (4, "Dora", 70.0)],
                )

                versions_a = S3DatasetVersionStore(artifacts_a, metadata_store=metadata_a)
                published_v1 = versions_a.get_published(DATASET_ID)
                self.assertIsNotNone(published_v1)
                assert published_v1 is not None

                parameters["revision"] = 2
                second = runner_a.run(job, parameters=parameters, fixture_mode=True)
                self.assertTrue(second.succeeded, second.error)
                second_load = metadata_a.list_target_loads(run_id=second.run_id)
                self.assertEqual(len(second_load), 1)
                self.assertEqual(second_load[0].status, TargetLoadStatus.SUCCESS.value)
                self.assertEqual(second_load[0].idempotency_action, IdempotencyAction.RELOAD.value)
                self.assertEqual(
                    self._rows(table),
                    [(1, "Alice", 92.0), (2, "Bob", 87.0), (3, "Carla", 80.0)],
                )

                all_versions = versions_a.list_versions(DATASET_ID)
                self.assertEqual(len(all_versions), 2)
                published_v2 = versions_a.get_published(DATASET_ID)
                self.assertIsNotNone(published_v2)
                assert published_v2 is not None
                self.assertNotEqual(published_v1.version_id, published_v2.version_id)
                self.assertEqual(published_v2.published_from_run_id, second.run_id)

                for version in all_versions:
                    self.assertTrue(
                        version.snapshot_uri.startswith(f"s3://{BUCKET}/{prefix}/datasets/")
                    )
                    snapshot_key = version.snapshot_uri.split(f"s3://{BUCKET}/", 1)[1]
                    snapshot_head = self.client.head_object(Bucket=BUCKET, Key=snapshot_key)
                    self.assertEqual(
                        snapshot_head["Metadata"]["pyingestkit-artifact-kind"],
                        "dataset-snapshot",
                    )

                diff_uri = artifacts_a.uri_for(
                    DATASET_ID,
                    UUID(second.run_id),
                    "reports/diff.json",
                )
                diff = json.loads(artifacts_a.read_bytes(diff_uri))
                self.assertEqual(
                    diff["summary"],
                    {"added": 1, "removed": 1, "changed": 1, "unchanged": 1},
                )
                self.assertTrue(str(diff_uri).startswith(f"s3://{BUCKET}/{prefix}/runs/"))

                source_raw = metadata_a.list_artifacts(second.run_id)
                self.assertEqual(len(source_raw), 1)
                self.assertIsNotNone(source_raw[0].storage_uri)
                assert source_raw[0].storage_uri is not None
                self.assertTrue(
                    source_raw[0].storage_uri.startswith(f"s3://{BUCKET}/{prefix}/runs/")
                )

                v2_fingerprint = published_v2.fingerprint.id
                shutil.rmtree(workspace_a)
                self.assertFalse(workspace_a.exists())
                self.assertFalse(workspace_b.exists())

                metadata_b = PostgresMetadataStore(self.dsn)
                metadata_b.initialize()
                artifacts_b = S3ArtifactStore(
                    bucket=BUCKET,
                    prefix=prefix,
                    cache_root=workspace_b,
                    endpoint_url=ENDPOINT,
                    region_name="us-east-1",
                )
                runner_b = Runner(artifacts_b, metadata_store=metadata_b)
                versions_b = S3DatasetVersionStore(artifacts_b, metadata_store=metadata_b)
                recovered_current = versions_b.get_published(DATASET_ID)
                self.assertIsNotNone(recovered_current)
                assert recovered_current is not None
                self.assertEqual(recovered_current.version_id, published_v2.version_id)
                recovered_dataset = versions_b.load_dataset(
                    versions_b.get_version(DATASET_ID, recovered_current.version_id)
                )
                self.assertEqual(recovered_current.fingerprint.id, v2_fingerprint)
                self.assertEqual(
                    recovered_dataset.to_rows(),
                    [
                        {"id": 1, "name": "Alice", "score": 92.0},
                        {"id": 2, "name": "Bob", "score": 87.0},
                        {"id": 3, "name": "Carla", "score": 80.0},
                    ],
                )

                registry = JobRegistry()
                registry.register(job)
                replay = ReplayService(runner_b, registry).replay(second.run_id)
                self.assertTrue(replay.succeeded)
                self.assertEqual(replay.verification_mode, "STRICT")
                self.assertTrue(replay.matched)
                self.assertEqual(replay.expected_fingerprint, v2_fingerprint)
                self.assertEqual(replay.actual_fingerprint, v2_fingerprint)

                replay_load = metadata_b.list_target_loads(run_id=replay.run.run_id)
                self.assertEqual(len(replay_load), 1)
                self.assertEqual(replay_load[0].status, TargetLoadStatus.SKIPPED.value)
                self.assertEqual(replay_load[0].idempotency_action, IdempotencyAction.SKIP.value)
                self.assertEqual(replay_load[0].rows_loaded, 0)
                self.assertEqual(
                    self._rows(table),
                    [(1, "Alice", 92.0), (2, "Bob", 87.0), (3, "Carla", 80.0)],
                )

                replay_raw = metadata_b.list_artifacts(replay.run.run_id)
                self.assertEqual(len(replay_raw), 1)
                self.assertEqual(replay_raw[0].sha256, source_raw[0].sha256)
                self.assertEqual(Path(replay_raw[0].path).read_bytes(), REVISION_2)
                self.assertTrue(Path(replay_raw[0].path).is_relative_to(workspace_b))
                self.assertIsNotNone(replay_raw[0].storage_uri)
                self.assertNotEqual(replay_raw[0].storage_uri, source_raw[0].storage_uri)

                remote_diff_after_host_a_loss = json.loads(artifacts_b.read_bytes(diff_uri))
                self.assertEqual(remote_diff_after_host_a_loss["summary"], diff["summary"])
                still_published = versions_b.get_published(DATASET_ID)
                self.assertIsNotNone(still_published)
                assert still_published is not None
                self.assertEqual(still_published.version_id, published_v2.version_id)
                self.assertEqual(still_published.published_from_run_id, second.run_id)

                replay_manifest_uri = artifacts_b.uri_for(
                    DATASET_ID,
                    UUID(replay.run.run_id),
                    "manifest.json",
                )
                replay_manifest = json.loads(artifacts_b.read_bytes(replay_manifest_uri))
                self.assertEqual(replay_manifest["replay"]["source_run_id"], second.run_id)
                self.assertTrue(replay_manifest["replay"]["matched"])
                self.assertEqual(replay_manifest["replay"]["actual_fingerprint"], v2_fingerprint)
                self.assertEqual(replay_manifest["replay"]["expected_fingerprint"], v2_fingerprint)
        finally:
            if old_target_dsn is None:
                os.environ.pop("PYINGEST_TARGET_DATABASE_URL", None)
            else:
                os.environ["PYINGEST_TARGET_DATABASE_URL"] = old_target_dsn
            if old_metadata_dsn is None:
                os.environ.pop("PYINGEST_DATABASE_URL", None)
            else:
                os.environ["PYINGEST_DATABASE_URL"] = old_metadata_dsn


if __name__ == "__main__":
    unittest.main()
