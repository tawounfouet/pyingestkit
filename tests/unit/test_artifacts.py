import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.provenance.hashing import sha256_bytes


class ArtifactTests(unittest.TestCase):
    def test_raw_artifact_is_hashed_and_written(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
