from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit_demo_jobs.local_file import job_definition

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner


class DemoJobTests(unittest.TestCase):
    def test_demo_job_ingests_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("demo\n", encoding="utf-8")
            workspace = root / "workspace"
            result = Runner(
                LocalArtifactStore(workspace),
                metadata_store=SQLiteMetadataStore.for_workspace(workspace),
            ).run(job_definition.build(), parameters={"path": str(source)})
            self.assertTrue(result.succeeded, result.error)
            self.assertEqual(result.job_id, "demo.local_file")
            self.assertEqual(len(result.steps), 1)


if __name__ == "__main__":
    unittest.main()
