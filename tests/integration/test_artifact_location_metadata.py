from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.metadata import SQLiteMetadataStore


class ArtifactLocationMetadataTests(unittest.TestCase):
    def test_storage_uri_is_persisted_additively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            artifact_store = LocalArtifactStore(workspace)
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            context = RunContext(
                job_id="demo.uri",
                job_version="0.6.0a2",
                artifact_store=artifact_store,
                run_id=uuid4(),
            )
            metadata.start_run(context)
            artifact = artifact_store.write_raw(
                context.job_id,
                context.run_id,
                name="sample.ndjson",
                data=b'{"id":1}\n',
                source_uri="https://example.invalid/sample.ndjson",
            )
            metadata.record_artifact(str(context.run_id), artifact)

            rows = metadata.list_artifacts(str(context.run_id))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].storage_uri, str(artifact.location_uri))
            self.assertIn("artifact_locations", inspect(metadata.engine).get_table_names())


if __name__ == "__main__":
    unittest.main()
