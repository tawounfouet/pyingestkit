from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit_demo_jobs.excel_quality import job_definition as excel_job_definition
from pyingestkit_demo_jobs.ndjson_quality import job_definition as ndjson_job_definition
from pyingestkit_demo_jobs.parquet_quality import job_definition as parquet_job_definition

from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner


class QualityFormatReferenceJobTests(unittest.TestCase):
    def _run_quality_job(self, job_definition) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(
                LocalArtifactStore(workspace),
                metadata_store=store,
            ).run(job_definition.build(), fixture_mode=True)

            self.assertTrue(result.succeeded, result.error)
            self.assertEqual(len(result.steps), 4)
            self.assertEqual(len(store.list_artifacts(result.run_id)), 1)
            validations = store.list_validations(result.run_id)
            self.assertEqual(validations[0].rule, "dataset_contract")
            self.assertEqual(validations[0].status, "PASSED")

            run_root = (
                workspace
                / "runs"
                / "demo"
                / job_definition.id.split(".")[-1]
                / result.run_id
            )
            manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
            report_pairs = {(entry["kind"], entry["path"]) for entry in manifest["reports"]}
            self.assertIn(("validation", "reports/validation.json"), report_pairs)
            self.assertIn(("profile", "reports/profile.json"), report_pairs)
            profile_path = run_root / "reports" / "profile.json"
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(profile["profile"]["row_count"], 2)
            self.assertEqual(profile["profile"]["duplicate_row_count"], 0)

            event_types = {event.event_type for event in store.list_events(result.run_id)}
            self.assertIn("VALIDATION_COMPLETED", event_types)
            self.assertIn("PROFILE_COMPLETED", event_types)
            self.assertIn("QUALITY_REPORT_WRITTEN", event_types)

    def test_ndjson_quality_reference_slice(self) -> None:
        self._run_quality_job(ndjson_job_definition)

    @unittest.skipUnless(
        importlib.util.find_spec("openpyxl"), "openpyxl optional extra not installed"
    )
    def test_excel_quality_reference_slice(self) -> None:
        self._run_quality_job(excel_job_definition)

    @unittest.skipUnless(
        importlib.util.find_spec("pyarrow"), "pyarrow optional extra not installed"
    )
    def test_parquet_quality_reference_slice(self) -> None:
        self._run_quality_job(parquet_job_definition)


if __name__ == "__main__":
    unittest.main()
