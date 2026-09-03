from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit import Job, Pipeline, RunContext, Step, ValidationIssue, ValidationResult
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner
from pyingestkit.validation import ValidationSeverity


class ValidValidation(Step):
    def execute(self, context: RunContext, data):
        return ValidationResult()


class InvalidValidation(Step):
    def execute(self, context: RunContext, data):
        return ValidationResult(
            (
                ValidationIssue(
                    "field.required",
                    "Required field 'id' is missing",
                    ValidationSeverity.ERROR,
                    field="id",
                    row_index=0,
                ),
            )
        )


class ValidationJob(Job):
    id = "demo.validation_runtime"

    def __init__(self, step: Step) -> None:
        self._step = step

    def pipeline(self) -> Pipeline:
        return Pipeline([self._step])


class ValidationRuntimeIntegrationTests(unittest.TestCase):
    def test_valid_result_is_persisted_manifested_and_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(
                ValidationJob(ValidValidation())
            )
            self.assertTrue(result.succeeded, result.error)
            validations = store.list_validations(result.run_id)
            self.assertEqual(len(validations), 1)
            self.assertEqual(validations[0].status, "PASSED")
            events = store.list_events(result.run_id)
            self.assertIn("VALIDATION_COMPLETED", {event.event_type for event in events})
            manifest_path = (
                workspace / "runs" / "demo" / "validation_runtime" / result.run_id / "manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["validations"][0]["valid"], True)

    def test_error_result_fails_run_after_persisting_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(
                ValidationJob(InvalidValidation())
            )
            self.assertFalse(result.succeeded)
            self.assertIn("ValidationError", result.error or "")
            validations = store.list_validations(result.run_id)
            self.assertEqual(validations[0].status, "FAILED")
            self.assertEqual(validations[1].rule, "field.required")
            self.assertEqual(validations[1].metadata["field"], "id")
            events = {event.event_type for event in store.list_events(result.run_id)}
            self.assertIn("VALIDATION_COMPLETED", events)
            self.assertIn("STEP_FAILED", events)
            self.assertIn("RUN_FAILED", events)


if __name__ == "__main__":
    unittest.main()
