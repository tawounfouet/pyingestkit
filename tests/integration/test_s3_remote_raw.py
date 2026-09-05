from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from pyingestkit_demo_jobs.versioned_ndjson import job_definition
from typer.testing import CliRunner

from pyingestkit.artifacts import S3ArtifactStore, StoredArtifact
from pyingestkit.cli.app import app
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
            prefix = f"b2/{uuid4().hex}"
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

            manifest_path = artifact_store.path_for(job.id, first.run_id, "manifest.json")
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(manifest_payload["reports"]), 2)
            for report in manifest_payload["reports"]:
                report_uri = artifact_store.uri_for(job.id, first.run_id, report["path"])
                self.assertTrue(str(report_uri).startswith(f"s3://{BUCKET}/{prefix}/runs/"))
                report_key = report_uri.key
                assert report_key is not None
                report_head = self.client.head_object(Bucket=BUCKET, Key=report_key)
                cached_report = artifact_store.path_for(job.id, first.run_id, report["path"])
                stored_report = StoredArtifact(
                    relative_path=report["path"],
                    path=str(cached_report),
                    storage_uri=str(report_uri),
                    content_type="application/json",
                    size_bytes=report_head["ContentLength"],
                    sha256=report_head["Metadata"]["pyingestkit-sha256"],
                )
                cached_report.unlink()
                self.assertEqual(artifact_store.materialize_artifact(stored_report), cached_report)

            manifest_uri = artifact_store.uri_for(job.id, first.run_id, "manifest.json")
            manifest_key = manifest_uri.key
            assert manifest_key is not None
            manifest_head = self.client.head_object(Bucket=BUCKET, Key=manifest_key)
            self.assertEqual(manifest_head["Metadata"]["pyingestkit-artifact-kind"], "manifest")
            stored_manifest = StoredArtifact(
                relative_path="manifest.json",
                path=str(manifest_path),
                storage_uri=str(manifest_uri),
                content_type="application/json",
                size_bytes=manifest_head["ContentLength"],
                sha256=manifest_head["Metadata"]["pyingestkit-sha256"],
            )
            manifest_path.unlink()
            self.assertEqual(artifact_store.materialize_artifact(stored_manifest), manifest_path)

            config_path = Path(tmp) / "pyingest-s3.json"
            config_path.write_text(
                json.dumps(
                    {
                        "runtime": {"workspace": str(workspace)},
                        "artifacts": {
                            "backend": "s3",
                            "s3": {
                                "bucket": BUCKET,
                                "prefix": prefix,
                                "region_name": "us-east-1",
                                "endpoint_url_env": "PYINGEST_TEST_S3_ENDPOINT_URL",
                                "cache_path": str(workspace),
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest_path.unlink()
            status_result = CliRunner().invoke(
                app, ["status", first.run_id, "--config", str(config_path), "--json"]
            )
            self.assertEqual(status_result.exit_code, 0, status_result.output)
            status_payload = json.loads(status_result.stdout)
            self.assertGreaterEqual(len(status_payload["reports"]), 2)
            self.assertTrue(all("path" in report for report in status_payload["reports"]))

            source_cache = Path(source.path)
            source_cache.unlink()
            self.assertFalse(source_cache.exists())

            registry = JobRegistry()
            registry.register(job)
            replay = ReplayService(runner, registry).replay(first.run_id)
            self.assertTrue(replay.succeeded)
            self.assertTrue(replay.matched)
            self.assertEqual(replay.verification_mode, "STRICT")
            self.assertIsNotNone(replay.expected_fingerprint)
            self.assertEqual(replay.actual_fingerprint, replay.expected_fingerprint)

            replay_records = metadata.list_artifacts(replay.run.run_id)
            self.assertEqual(len(replay_records), 1)
            replay_raw = replay_records[0]
            self.assertIsNotNone(replay_raw.storage_uri)
            self.assertEqual(replay_raw.sha256, source.sha256)
            self.assertTrue(Path(replay_raw.path).is_file())
            self.assertNotEqual(replay_raw.storage_uri, source.storage_uri)

            replay_manifest_uri = artifact_store.uri_for(job.id, replay.run.run_id, "manifest.json")
            replay_manifest_bytes = artifact_store.read_bytes(replay_manifest_uri)
            replay_manifest = json.loads(replay_manifest_bytes)
            self.assertEqual(replay_manifest["replay"]["source_run_id"], first.run_id)
            self.assertTrue(replay_manifest["replay"]["matched"])
            self.assertEqual(
                replay_manifest["replay"]["actual_fingerprint"],
                replay_manifest["replay"]["expected_fingerprint"],
            )


if __name__ == "__main__":
    unittest.main()
