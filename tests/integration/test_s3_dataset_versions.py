from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from pyingestkit.artifacts import S3ArtifactStore
from pyingestkit.cli.app import app
from pyingestkit.dataset import Dataset
from pyingestkit.versioning import S3DatasetVersionStore

ENDPOINT = os.getenv("PYINGEST_TEST_S3_ENDPOINT_URL")
BUCKET = os.getenv("PYINGEST_TEST_S3_BUCKET")


@unittest.skipUnless(ENDPOINT and BUCKET, "S3-compatible endpoint and bucket are required")
class S3DatasetVersionIntegrationTests(unittest.TestCase):
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

    def test_versions_and_publication_are_cross_workspace_durable(self) -> None:
        assert ENDPOINT is not None
        assert BUCKET is not None
        prefix = f"b2/{uuid4().hex}"
        with tempfile.TemporaryDirectory() as first_tmp:
            first_artifacts = S3ArtifactStore(
                bucket=BUCKET,
                prefix=prefix,
                cache_root=Path(first_tmp) / ".pyingest",
                endpoint_url=ENDPOINT,
                region_name="us-east-1",
            )
            first_store = S3DatasetVersionStore(first_artifacts)
            first = first_store.create_version(
                Dataset([{"id": 1, "name": "Alice"}]),
                dataset_id="demo.cross_host",
                created_from_run_id="runner-a",
                job_id="demo.cross_host",
                job_version="1.0.0",
            )
            first_store.publish(first, run_id="runner-a")
            self.assertTrue(first.snapshot_uri.startswith(f"s3://{BUCKET}/{prefix}/datasets/"))

        with tempfile.TemporaryDirectory() as second_tmp:
            second_workspace = Path(second_tmp) / ".pyingest"
            self.assertFalse(second_workspace.exists())
            second_artifacts = S3ArtifactStore(
                bucket=BUCKET,
                prefix=prefix,
                cache_root=second_workspace,
                endpoint_url=ENDPOINT,
                region_name="us-east-1",
            )
            second_store = S3DatasetVersionStore(second_artifacts)
            published = second_store.get_published("demo.cross_host")
            self.assertIsNotNone(published)
            assert published is not None
            recovered = second_store.load_dataset(
                second_store.get_version("demo.cross_host", published.version_id)
            )
            self.assertEqual(recovered.to_rows(), [{"id": 1, "name": "Alice"}])

            second = second_store.create_version(
                Dataset([{"id": 1, "name": "Alicia"}, {"id": 2, "name": "Bob"}]),
                dataset_id="demo.cross_host",
                created_from_run_id="runner-b",
                job_id="demo.cross_host",
                job_version="1.0.1",
            )
            current = second_store.publish(second, run_id="runner-b")
            self.assertEqual(current.version_id, second.version_id)
            self.assertEqual(len(second_store.list_versions("demo.cross_host")), 2)

            config_path = Path(second_tmp) / "pyingest-s3.json"
            config_path.write_text(
                json.dumps(
                    {
                        "runtime": {"workspace": str(second_workspace)},
                        "artifacts": {
                            "backend": "s3",
                            "s3": {
                                "bucket": BUCKET,
                                "prefix": prefix,
                                "region_name": "us-east-1",
                                "endpoint_url_env": "PYINGEST_TEST_S3_ENDPOINT_URL",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            cli = CliRunner()
            versions_result = cli.invoke(
                app,
                ["versions", "demo.cross_host", "--config", str(config_path), "--json"],
            )
            self.assertEqual(versions_result.exit_code, 0, versions_result.output)
            self.assertEqual(len(json.loads(versions_result.stdout)), 2)
            published_result = cli.invoke(
                app,
                ["published", "demo.cross_host", "--config", str(config_path), "--json"],
            )
            self.assertEqual(published_result.exit_code, 0, published_result.output)
            self.assertEqual(
                json.loads(published_result.stdout)["version_id"],
                second.version_id,
            )

            pointer_key = f"{prefix}/datasets/published/demo/cross_host/current.json"
            pointer_head = self.client.head_object(Bucket=BUCKET, Key=pointer_key)
            self.assertEqual(
                pointer_head["Metadata"]["pyingestkit-artifact-kind"],
                "published-dataset",
            )

        with tempfile.TemporaryDirectory() as third_tmp:
            third_workspace = Path(third_tmp) / ".pyingest"
            third_artifacts = S3ArtifactStore(
                bucket=BUCKET,
                prefix=prefix,
                cache_root=third_workspace,
                endpoint_url=ENDPOINT,
                region_name="us-east-1",
            )
            third_store = S3DatasetVersionStore(third_artifacts)
            current = third_store.get_published("demo.cross_host")
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.version_id, second.version_id)
            self.assertEqual(
                third_store.load_dataset(
                    third_store.get_version("demo.cross_host", current.version_id)
                ).to_rows(),
                [{"id": 1, "name": "Alicia"}, {"id": 2, "name": "Bob"}],
            )
            self.assertFalse(third_workspace.exists())


if __name__ == "__main__":
    unittest.main()
