import tempfile
import unittest
from pathlib import Path

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.sources import LocalSource


class LocalSourceTests(unittest.TestCase):
    def test_fetch_copies_source_to_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = root / "input.csv"
            source_path.write_text("id,name\n1,A\n", encoding="utf-8")
            store = LocalArtifactStore(root / "workspace")
            context = RunContext(job_id="demo.local", job_version="0.1.0", artifact_store=store)
            artifact = LocalSource(source_path).fetch(context)
            self.assertTrue(Path(artifact.path).exists())
            self.assertEqual(Path(artifact.path).read_bytes(), source_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
