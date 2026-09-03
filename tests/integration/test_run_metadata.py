from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner


class Pass(Step):
    def execute(self, context: RunContext, data):
        return data


class Demo(Job):
    id = "demo.persisted"
    version = "9.9.9"

    def pipeline(self) -> Pipeline:
        return Pipeline([Pass()])


class RunMetadataTests(unittest.TestCase):
    def test_run_and_step_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(
                Demo(), parameters={"token": "secret", "safe": 1}
            )
            run = store.get_run(result.run_id)
            self.assertEqual(run.status, "SUCCESS")
            self.assertEqual(run.job_version, "9.9.9")
            self.assertEqual(run.parameters["token"], "***REDACTED***")
            self.assertEqual(run.parameters["safe"], 1)
            self.assertEqual(store.list_steps(result.run_id)[0].status, "SUCCESS")


if __name__ == "__main__":
    unittest.main()
