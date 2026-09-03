from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner
from pyingestkit.sources import LocalSource


class Fetch(Step):
    def execute(self, context: RunContext, data):
        return LocalSource(Path(str(context.parameter("path")))).fetch(context)


class Demo(Job):
    id = "demo.manifest_artifact"

    def pipeline(self) -> Pipeline:
        return Pipeline([Fetch()])


class ManifestArtifactTests(unittest.TestCase):
    def test_raw_artifact_is_in_manifest_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.txt"
            source.write_text("hello", encoding="utf-8")
            workspace = root / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(
                Demo(), parameters={"path": str(source)}
            )
            manifest = next(workspace.rglob("manifest.json"))
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["artifacts"]), 1)
            self.assertIn("T", payload["started_at"])
            self.assertIn("T", payload["artifacts"][0]["retrieved_at"])
            self.assertEqual(len(store.list_artifacts(result.run_id)), 1)
            self.assertEqual(
                payload["artifacts"][0]["sha256"],
                store.list_artifacts(result.run_id)[0].sha256,
            )


if __name__ == "__main__":
    unittest.main()
