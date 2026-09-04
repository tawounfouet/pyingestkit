from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from pyingestkit import (
    Dataset,
    DatasetContract,
    DatasetProfiler,
    FieldContract,
    Job,
    Pipeline,
    RunContext,
    Step,
)
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.cli.app import app
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner


class ProduceQualityEvidence(Step):
    def execute(self, context: RunContext, data):
        dataset = Dataset(
            [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            source_artifact_id="raw-fixture",
        )
        validation = DatasetContract(
            fields=(
                FieldContract("id", nullable=False, expected_type=int, unique=True),
                FieldContract("name", nullable=False, expected_type=str),
            )
        ).validate(dataset)
        profile = DatasetProfiler().profile(dataset)
        return {"dataset": dataset, "validation": validation, "profile": profile}


class QualityJob(Job):
    id = "demo.quality_reports"

    def pipeline(self) -> Pipeline:
        return Pipeline([ProduceQualityEvidence()])


class QualityReportsRuntimeTests(unittest.TestCase):
    def test_validation_and_profile_reports_are_materialized_and_manifested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(QualityJob())

            self.assertTrue(result.succeeded, result.error)
            run_root = workspace / "runs" / "demo" / "quality_reports" / result.run_id
            validation_path = run_root / "reports" / "validation.json"
            profile_path = run_root / "reports" / "profile.json"
            self.assertTrue(validation_path.is_file())
            self.assertTrue(profile_path.is_file())

            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            self.assertEqual(validation["kind"], "validation")
            self.assertEqual(validation["validations"][0]["valid"], True)
            self.assertEqual(profile["kind"], "profile")
            self.assertEqual(profile["profile"]["row_count"], 2)
            self.assertNotIn("dataset", profile)

            manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
            report_pairs = {(entry["kind"], entry["path"]) for entry in manifest["reports"]}
            self.assertIn(("validation", "reports/validation.json"), report_pairs)
            self.assertIn(("profile", "reports/profile.json"), report_pairs)

            event_types = {event.event_type for event in store.list_events(result.run_id)}
            self.assertIn("VALIDATION_COMPLETED", event_types)
            self.assertIn("PROFILE_COMPLETED", event_types)
            self.assertIn("QUALITY_REPORT_WRITTEN", event_types)

            status_result = CliRunner().invoke(
                app,
                ["status", result.run_id[:8], "--workspace", str(workspace), "--json"],
            )
            self.assertEqual(status_result.exit_code, 0, status_result.output)
            status_payload = json.loads(status_result.stdout)
            status_reports = {
                (entry["kind"], entry["path"]) for entry in status_payload["reports"]
            }
            self.assertEqual(status_reports, report_pairs)


if __name__ == "__main__":
    unittest.main()
