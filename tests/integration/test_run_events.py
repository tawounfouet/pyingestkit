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
    id = "demo.events_persisted"
    def pipeline(self) -> Pipeline:
        return Pipeline([Pass()])


class RunEventsTests(unittest.TestCase):
    def test_structural_events_are_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(Demo())
            types = [row.event_type for row in store.list_events(result.run_id)]
            self.assertEqual(types, ["RUN_STARTED", "STEP_STARTED", "STEP_SUCCEEDED", "RUN_SUCCEEDED"])


if __name__ == "__main__":
    unittest.main()
