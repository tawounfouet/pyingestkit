from __future__ import annotations

import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner
from pyingestkit_demo_jobs.http_csv import job_definition as csv_job_definition
from pyingestkit_demo_jobs.http_json import job_definition as json_job_definition


class HttpDemoJobTests(unittest.TestCase):
    def _run_offline(self, job_definition):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            store = SQLiteMetadataStore.for_workspace(workspace)
            with patch.object(
                socket.socket,
                "connect",
                side_effect=AssertionError("reference HTTP tests must stay offline"),
            ):
                result = Runner(
                    LocalArtifactStore(workspace),
                    metadata_store=store,
                ).run(job_definition.build(), fixture_mode=True)
            self.assertTrue(result.succeeded, result.error)
            self.assertEqual(len(result.steps), 3)
            artifacts = store.list_artifacts(result.run_id)
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0].status_code, 200)
            self.assertIn("fixtures.pyingestkit.invalid", artifacts[0].source_uri)
            validations = store.list_validations(result.run_id)
            self.assertEqual(validations[0].rule, "dataset_contract")
            self.assertEqual(validations[0].status, "PASSED")
            event_types = {event.event_type for event in store.list_events(result.run_id)}
            self.assertIn("VALIDATION_COMPLETED", event_types)
            manifest_path = workspace / "runs" / "demo" / job_definition.id.split(".")[-1]
            manifests = list(manifest_path.glob("*/manifest.json"))
            self.assertEqual(len(manifests), 1)
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "SUCCESS")
            self.assertEqual(len(manifest["artifacts"]), 1)
            self.assertEqual(manifest["validations"][0]["valid"], True)
            return result

    def test_http_csv_reference_slice_is_fully_offline(self) -> None:
        result = self._run_offline(csv_job_definition)
        self.assertEqual(result.job_id, "demo.http_csv")

    def test_http_json_reference_slice_is_fully_offline(self) -> None:
        result = self._run_offline(json_job_definition)
        self.assertEqual(result.job_id, "demo.http_json")


if __name__ == "__main__":
    unittest.main()
