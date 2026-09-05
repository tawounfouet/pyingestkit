from __future__ import annotations

import io
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import uuid4

from pyingestkit.artifacts import ArtifactURI, S3ArtifactStore
from pyingestkit.core.exceptions import ConfigurationError, StorageError


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
        return {"Metadata": dict(item["Metadata"]), "ContentLength": len(item["Body"])}

    def put_object(self, **kwargs: Any) -> Mapping[str, Any]:
        bucket = str(kwargs["Bucket"])
        key = str(kwargs["Key"])
        identity = (bucket, key)
        if identity in self.objects:
            raise FakeS3Error("PreconditionFailed")
        self.objects[identity] = dict(kwargs)
        return {"ETag": '"fake"'}

    def get_object(self, *, Bucket: str, Key: str) -> Mapping[str, Any]:
        try:
            item = self.objects[(Bucket, Key)]
        except KeyError as exc:
            raise FakeS3Error("NoSuchKey") from exc
        return {"Body": io.BytesIO(item["Body"]), "Metadata": dict(item["Metadata"])}


class S3ArtifactStoreTests(unittest.TestCase):
    def test_remote_raw_is_immutable_uri_addressable_and_cache_recoverable(self) -> None:
        client = FakeS3Client()
        with tempfile.TemporaryDirectory() as tmp:
            store = S3ArtifactStore(
                bucket="demo-bucket",
                prefix="tenant/raw",
                cache_root=tmp,
                client=client,
            )
            run_id = uuid4()
            artifact = store.write_raw(
                "demo.remote",
                run_id,
                name="people data.ndjson",
                data=b'{"id":1}\n',
                source_uri="https://example.invalid/people.ndjson",
                content_type="application/x-ndjson",
            )
            location = artifact.location_uri
            self.assertEqual(location.scheme, "s3")
            self.assertEqual(location.bucket, "demo-bucket")
            self.assertIn("tenant/raw/runs/demo/remote/", location.key or "")
            self.assertEqual(Path(artifact.path).read_bytes(), b'{"id":1}\n')

            key = location.key
            assert key is not None
            remote = client.objects[("demo-bucket", key)]
            self.assertEqual(remote["Metadata"]["pyingestkit-sha256"], artifact.sha256)
            self.assertEqual(remote["ContentType"], "application/x-ndjson")

            Path(artifact.path).unlink()
            self.assertFalse(Path(artifact.path).exists())
            self.assertEqual(store.materialize_raw(artifact), Path(artifact.path))
            self.assertEqual(Path(artifact.path).read_bytes(), b'{"id":1}\n')

            with self.assertRaisesRegex(StorageError, "immutable"):
                store.write_raw(
                    "demo.remote",
                    run_id,
                    name="people data.ndjson",
                    data=b'{"id":2}\n',
                    source_uri="https://example.invalid/people.ndjson",
                )

    def test_store_refuses_other_bucket_and_credential_bearing_endpoint(self) -> None:
        client = FakeS3Client()
        with tempfile.TemporaryDirectory() as tmp:
            store = S3ArtifactStore(bucket="one", cache_root=tmp, client=client)
            with self.assertRaises(StorageError):
                store.read_bytes(ArtifactURI.s3("two", "raw/file"))
            with self.assertRaises(ConfigurationError):
                S3ArtifactStore(
                    bucket="one",
                    cache_root=tmp,
                    endpoint_url="https://user:secret@s3.example",
                    client=client,
                )


if __name__ == "__main__":
    unittest.main()
