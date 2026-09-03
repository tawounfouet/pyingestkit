from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.runtime import Runner
from pyingestkit_demo_jobs.local_file import job


class DemoJobTests(unittest.TestCase):
    def test_demo_job_ingests_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("demo\n", encoding="utf-8")
            result = Runner(LocalArtifactStore(root / "workspace")).run(
                job, parameters={"path": str(source)}
            )
            self.assertTrue(result.succeeded, result.error)
            self.assertEqual(result.job_id, "demo.local_file")
            self.assertEqual(len(result.steps), 1)


if __name__ == "__main__":
    unittest.main()
