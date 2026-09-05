import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from pyingestkit.artifacts import ArtifactURI, LocalArtifactStore
from pyingestkit.provenance.hashing import sha256_bytes


class ArtifactTests(unittest.TestCase):
    def test_raw_artifact_is_hashed_written_and_uri_addressable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(tmp)
            run_id = uuid4()
            data = b"hello"
            artifact = store.write_raw(
                "demo.raw",
                run_id,
                name="sample.txt",
                data=data,
                source_uri="file:///sample.txt",
                content_type="text/plain",
            )
            self.assertEqual(artifact.sha256, sha256_bytes(data))
            self.assertEqual(Path(artifact.path).read_bytes(), data)
            self.assertEqual(artifact.size_bytes, len(data))
            self.assertEqual(artifact.location_uri.scheme, "file")
            self.assertEqual(store.read_bytes(artifact.location_uri), data)
            self.assertEqual(store.materialize_raw(artifact), Path(artifact.path))
            self.assertEqual(
                ArtifactURI(artifact.storage_uri or "").as_path(),
                Path(artifact.path).absolute(),
            )

    def test_raw_materialization_detects_local_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(tmp)
            artifact = store.write_raw(
                "demo.raw",
                uuid4(),
                name="sample.txt",
                data=b"original",
                source_uri="file:///sample.txt",
            )
            Path(artifact.path).write_bytes(b"tampered")
            with self.assertRaisesRegex(Exception, "SHA-256 mismatch"):
                store.materialize_raw(artifact)


if __name__ == "__main__":
    unittest.main()
