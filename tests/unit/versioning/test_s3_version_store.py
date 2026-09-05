from __future__ import annotations

import io
import tempfile
import unittest
from collections.abc import Mapping
from typing import Any

from pyingestkit.artifacts import S3ArtifactStore
from pyingestkit.core.exceptions import VersionStoreError
from pyingestkit.dataset import Dataset
from pyingestkit.versioning import (
    DatasetVersionStore,
    FilesystemDatasetVersionStore,
    S3DatasetVersionStore,
)


class FakeS3Error(RuntimeError):
    def __init__(self, code: str) -> None:
        self.response = {"Error": {"Code": code}}
        super().__init__(f"fake s3 error {code}")


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}

    def head_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]:
        try:
            item = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeS3Error("404") from exc
        return {
            "Metadata": dict(item.get("Metadata", {})),
            "ContentLength": len(item["Body"]),
        }

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]:
        identity = (str(kwargs["Bucket"]), str(kwargs["Key"]))
        if identity in self.objects and kwargs.get("IfNoneMatch") == "*":
            raise FakeS3Error("PreconditionFailed")
        self.objects[identity] = dict(kwargs)
        return {"ETag": '"fake"'}

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]:
        try:
            item = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeS3Error("NoSuchKey") from exc
        return {
            "Body": io.BytesIO(item["Body"]),
            "Metadata": dict(item.get("Metadata", {})),
        }

    def list_objects_v2(self, **kwargs: Any) -> Mapping[str, Any]:
        bucket = str(kwargs["Bucket"])
        prefix = str(kwargs.get("Prefix", ""))
        keys = sorted(key for item_bucket, key in self.objects if item_bucket == bucket)
        return {
            "Contents": [{"Key": key} for key in keys if key.startswith(prefix)],
            "IsTruncated": False,
        }


def assert_version_store_contract(
    test_case: unittest.TestCase,
    store: DatasetVersionStore,
) -> None:
    first = store.create_version(
        Dataset([{"id": 1, "name": "Alice"}]),
        dataset_id="demo.contract",
        created_from_run_id="run-1",
        job_id="demo.contract",
        job_version="1.0.0",
    )
    same = store.create_version(
        Dataset([{"id": 1, "name": "Alice"}]),
        dataset_id="demo.contract",
        created_from_run_id="run-2",
        job_id="demo.contract",
        job_version="1.0.0",
    )
    second = store.create_version(
        Dataset([{"id": 1, "name": "Alicia"}]),
        dataset_id="demo.contract",
        created_from_run_id="run-3",
        job_id="demo.contract",
        job_version="1.0.1",
    )

    test_case.assertEqual(first.version_id, same.version_id)
    test_case.assertNotEqual(first.version_id, second.version_id)
    test_case.assertEqual(len(store.list_versions("demo.contract")), 2)
    test_case.assertEqual(
        store.load_dataset(first).to_rows(),
        [{"id": 1, "name": "Alice"}],
    )

    published_first = store.publish(first, run_id="run-1")
    published_same = store.publish(first, run_id="run-2")
    test_case.assertEqual(published_first.published_at, published_same.published_at)

    published_second = store.publish(second, run_id="run-3")
    current = store.get_published("demo.contract")
    test_case.assertIsNotNone(current)
    assert current is not None
    test_case.assertEqual(current.version_id, published_second.version_id)
    test_case.assertEqual(
        store.load_dataset(second).to_rows(),
        [{"id": 1, "name": "Alicia"}],
    )


class S3DatasetVersionStoreTests(unittest.TestCase):
    def test_filesystem_and_s3_pass_the_same_version_store_contract(self) -> None:
        client = FakeS3Client()
        with (
            tempfile.TemporaryDirectory() as filesystem_root,
            tempfile.TemporaryDirectory() as s3_cache,
        ):
            stores: tuple[tuple[str, DatasetVersionStore], ...] = (
                ("filesystem", FilesystemDatasetVersionStore(filesystem_root)),
                (
                    "s3",
                    S3DatasetVersionStore(
                        S3ArtifactStore(
                            bucket="demo-bucket",
                            prefix="tenant",
                            cache_root=s3_cache,
                            client=client,
                        )
                    ),
                ),
            )
            for name, store in stores:
                with self.subTest(store=name):
                    assert_version_store_contract(self, store)

    def test_versions_and_publication_survive_an_empty_local_workspace(self) -> None:
        client = FakeS3Client()
        with (
            tempfile.TemporaryDirectory() as first_cache,
            tempfile.TemporaryDirectory() as second_cache,
        ):
            first_artifacts = S3ArtifactStore(
                bucket="demo-bucket",
                prefix="tenant",
                cache_root=first_cache,
                client=client,
            )
            first_store = S3DatasetVersionStore(first_artifacts)
            version_one = first_store.create_version(
                Dataset([{"id": 1, "name": "Alice"}]),
                dataset_id="demo.reference",
                created_from_run_id="run-1",
                job_id="demo.reference",
                job_version="1.0.0",
            )
            same = first_store.create_version(
                Dataset([{"id": 1, "name": "Alice"}]),
                dataset_id="demo.reference",
                created_from_run_id="run-2",
                job_id="demo.reference",
                job_version="1.0.0",
            )
            self.assertEqual(version_one.version_id, same.version_id)
            self.assertTrue(
                version_one.snapshot_uri.startswith("s3://demo-bucket/tenant/datasets/")
            )
            first_published = first_store.publish(version_one, run_id="run-1")
            same_published = first_store.publish(version_one, run_id="run-2")
            self.assertEqual(first_published.published_at, same_published.published_at)

            second_artifacts = S3ArtifactStore(
                bucket="demo-bucket",
                prefix="tenant",
                cache_root=second_cache,
                client=client,
            )
            second_store = S3DatasetVersionStore(second_artifacts)
            recovered = second_store.get_published("demo.reference")
            self.assertIsNotNone(recovered)
            assert recovered is not None
            self.assertEqual(recovered.version_id, version_one.version_id)
            self.assertEqual(
                second_store.load_dataset(
                    second_store.get_version("demo.reference", version_one.version_id)
                ).to_rows(),
                [{"id": 1, "name": "Alice"}],
            )

            version_two = second_store.create_version(
                Dataset([{"id": 1, "name": "Alicia"}]),
                dataset_id="demo.reference",
                created_from_run_id="run-3",
                job_id="demo.reference",
                job_version="1.0.1",
            )
            current = second_store.publish(version_two, run_id="run-3")
            self.assertEqual(current.version_id, version_two.version_id)
            self.assertEqual(len(second_store.list_versions("demo.reference")), 2)

    def test_missing_snapshot_is_rejected_explicitly(self) -> None:
        client = FakeS3Client()
        with tempfile.TemporaryDirectory() as cache:
            artifacts = S3ArtifactStore(
                bucket="demo-bucket",
                prefix="tenant",
                cache_root=cache,
                client=client,
            )
            store = S3DatasetVersionStore(artifacts)
            version = store.create_version(
                Dataset([{"id": 1}]),
                dataset_id="demo.reference",
                created_from_run_id="run-1",
                job_id="demo.reference",
                job_version="1.0.0",
            )
            snapshot_key = version.snapshot_uri.split("s3://demo-bucket/", 1)[1]
            del client.objects[("demo-bucket", snapshot_key)]
            with self.assertRaisesRegex(VersionStoreError, "Snapshot object is missing"):
                store.load_dataset(version)

    def test_snapshot_hash_mismatch_is_rejected(self) -> None:
        client = FakeS3Client()
        with tempfile.TemporaryDirectory() as cache:
            artifacts = S3ArtifactStore(
                bucket="demo-bucket",
                prefix="tenant",
                cache_root=cache,
                client=client,
            )
            store = S3DatasetVersionStore(artifacts)
            version = store.create_version(
                Dataset([{"id": 1}]),
                dataset_id="demo.reference",
                created_from_run_id="run-1",
                job_id="demo.reference",
                job_version="1.0.0",
            )
            snapshot_key = version.snapshot_uri.split("s3://demo-bucket/", 1)[1]
            client.objects[("demo-bucket", snapshot_key)]["Body"] = b"{}"
            with self.assertRaisesRegex(VersionStoreError, "SHA-256 mismatch"):
                store.load_dataset(version)
            with self.assertRaisesRegex(VersionStoreError, "SHA-256 mismatch"):
                store.create_version(
                    Dataset([{"id": 1}]),
                    dataset_id="demo.reference",
                    created_from_run_id="run-2",
                    job_id="demo.reference",
                    job_version="1.0.0",
                )

    def test_invalid_dataset_id_is_rejected(self) -> None:
        client = FakeS3Client()
        with tempfile.TemporaryDirectory() as cache:
            artifacts = S3ArtifactStore(
                bucket="demo-bucket",
                cache_root=cache,
                client=client,
            )
            store = S3DatasetVersionStore(artifacts)
            with self.assertRaises(VersionStoreError):
                store.create_version(
                    Dataset([{"id": 1}]),
                    dataset_id="../escape",
                    created_from_run_id="run-1",
                    job_id="demo.reference",
                    job_version="1.0.0",
                )


if __name__ == "__main__":
    unittest.main()
