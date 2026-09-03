from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit import RunContext, Runner, job, step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore


class DeclarativeIntegrationTests(unittest.TestCase):
    def test_declarative_compiles_to_same_runner(self) -> None:
        @step
        def add_one(data=None):
            return int(data or 0) + 1

        @step
        def inspect_context(context: RunContext, data=None):
            return int(data or 0) + int(context.parameter("increment", 0))

        @job(id="demo.declarative_integration")
        def pipeline() -> None:
            add_one()
            inspect_context()

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            result = Runner(
                LocalArtifactStore(workspace),
                metadata_store=SQLiteMetadataStore.for_workspace(workspace),
            ).run(pipeline.build(), initial_data=1, parameters={"increment": 5})
            self.assertTrue(result.succeeded, result.error)
            self.assertEqual(result.steps[-1].output, 7)


if __name__ == "__main__":
    unittest.main()
