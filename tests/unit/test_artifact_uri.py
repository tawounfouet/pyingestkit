from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit.artifacts import ArtifactURI
from pyingestkit.artifacts.naming import relative_artifact_path
from pyingestkit.core.exceptions import StorageError


class ArtifactURITests(unittest.TestCase):
    def test_file_uri_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "raw data.ndjson"
            uri = ArtifactURI.from_path(path)
            self.assertEqual(uri.scheme, "file")
            self.assertTrue(uri.is_local)
            self.assertEqual(uri.as_path(), path.absolute())
            self.assertEqual(uri.name, "raw data.ndjson")

    def test_s3_uri_preserves_bucket_and_key(self) -> None:
        uri = ArtifactURI.s3("demo-bucket", "root/runs/abc/raw/a b.ndjson")
        self.assertEqual(str(uri), "s3://demo-bucket/root/runs/abc/raw/a%20b.ndjson")
        self.assertEqual(uri.bucket, "demo-bucket")
        self.assertEqual(uri.key, "root/runs/abc/raw/a b.ndjson")
        self.assertEqual(uri.name, "a b.ndjson")
        self.assertFalse(uri.is_local)

    def test_uri_rejects_credentials_query_and_fragment(self) -> None:
        for value in (
            "s3://user:secret@bucket/key",
            "s3://bucket/key?token=secret",
            "s3://bucket/key#fragment",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ArtifactURI(value)

    def test_relative_artifact_path_rejects_escape(self) -> None:
        for value in ("../secret", "reports/../../secret", "/absolute", r"raw\escape"):
            with self.subTest(value=value), self.assertRaises(StorageError):
                relative_artifact_path(value)

    def test_v05_artifact_store_abstract_surface_is_unchanged(self) -> None:
        from pyingestkit.artifacts import ArtifactStore

        self.assertEqual(
            ArtifactStore.__abstractmethods__,
            frozenset({"prepare_run", "write_raw", "write_json", "path_for"}),
        )


if __name__ == "__main__":
    unittest.main()
