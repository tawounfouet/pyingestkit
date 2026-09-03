from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit import Dataset, Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.runtime import Runner


class ProduceDataset(Step):
    def execute(self, context: RunContext, data):
        return Dataset([{"id": "001"}])


class DatasetJob(Job):
    id = "demo.manifest_dataset"

    def pipeline(self) -> Pipeline:
        return Pipeline([ProduceDataset()])


class ManifestStepOutputTests(unittest.TestCase):
    def test_manifest_records_step_metadata_without_serializing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            result = Runner(LocalArtifactStore(workspace)).run(DatasetJob())

            self.assertTrue(result.succeeded, result.error)
            manifest_path = (
                workspace / "runs" / "demo" / "manifest_dataset" / result.run_id / "manifest.json"
            )
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["steps"][0]["step_name"], "ProduceDataset")
            self.assertEqual(payload["steps"][0]["status"], "SUCCESS")
            self.assertNotIn("output", payload["steps"][0])


if __name__ == "__main__":
    unittest.main()
