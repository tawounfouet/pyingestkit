import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from pyingestkit import Job, Pipeline, RunContext, RunStatus, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.runtime import Runner


class AddOne(Step):
    def execute(self, context: RunContext, data: Any) -> Any:
        return int(data or 0) + 1


class DemoJob(Job):
    id = "demo.runner"
    version = "0.1.0"

    def pipeline(self) -> Pipeline:
        return Pipeline([AddOne(), AddOne()])


class RunnerTests(unittest.TestCase):
    def test_run_succeeds_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalArtifactStore(tmp)
            result = Runner(store).run(DemoJob(), initial_data=0)
            self.assertEqual(result.status, RunStatus.SUCCESS)
            self.assertEqual(len(result.steps), 2)
            manifest = next(Path(tmp).rglob("manifest.json"))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "SUCCESS")
            self.assertEqual(payload["job_id"], "demo.runner")


if __name__ == "__main__":
    unittest.main()
