from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from pyingestkit import Dataset, DatasetDiffer, DiffPolicy, Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.artifacts.raw import RawArtifact
from pyingestkit.cli.app import app
from pyingestkit.core.events import Event
from pyingestkit.core.result import RunResult, StepResult
from pyingestkit.metadata import (
    ArtifactRecord,
    EventRecord,
    MetadataStore,
    PublicationRecord,
    RunRecord,
    SQLiteMetadataStore,
    StepRecord,
    ValidationRecord,
)
from pyingestkit.runtime import Runner


class ProduceDiff(Step):
    def execute(self, context: RunContext, data: Any) -> Any:
        previous = Dataset(
            [
                {"id": 1, "name": "A", "api_token": "old-secret"},
                {"id": 2, "name": "B", "api_token": "keep-secret"},
            ]
        )
        candidate = Dataset(
            [
                {"id": 1, "name": "A2", "api_token": "new-secret"},
                {"id": 3, "name": "C", "api_token": "another-secret"},
            ]
        )
        return DatasetDiffer(
            DiffPolicy(key_fields=("id",), capture_values=True, max_entries=10)
        ).compare(previous, candidate)


class DiffJob(Job):
    id = "demo.diff_reports"
    version = "0.4.0b2"

    def pipeline(self) -> Pipeline:
        return Pipeline([ProduceDiff()])


class LegacyMetadataStore(MetadataStore):
    """V0.3-compatible wrapper intentionally lacking DiffMetadataCapability."""

    def __init__(self, delegate: SQLiteMetadataStore) -> None:
        self.delegate = delegate

    def initialize(self) -> None:
        self.delegate.initialize()

    def start_run(self, context: RunContext) -> None:
        self.delegate.start_run(context)

    def finish_run(self, result: RunResult) -> None:
        self.delegate.finish_run(result)

    def record_step(self, run_id: str, position: int, result: StepResult) -> None:
        self.delegate.record_step(run_id, position, result)

    def record_artifact(self, run_id: str, artifact: RawArtifact, *, kind: str = "raw") -> None:
        self.delegate.record_artifact(run_id, artifact, kind=kind)

    def record_event(self, event: Event) -> None:
        self.delegate.record_event(event)

    def record_validation(
        self,
        run_id: str,
        *,
        rule: str,
        severity: str,
        status: str,
        message: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.delegate.record_validation(
            run_id,
            rule=rule,
            severity=severity,
            status=status,
            message=message,
            metadata=metadata,
        )

    def record_publication(
        self,
        run_id: str,
        *,
        dataset_id: str,
        status: str,
        candidate_path: str | None = None,
        published_path: str | None = None,
        published_at: datetime | None = None,
    ) -> None:
        self.delegate.record_publication(
            run_id,
            dataset_id=dataset_id,
            status=status,
            candidate_path=candidate_path,
            published_path=published_path,
            published_at=published_at,
        )

    def list_runs(
        self,
        *,
        job_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> tuple[RunRecord, ...]:
        return self.delegate.list_runs(job_id=job_id, status=status, limit=limit)

    def get_run(self, run_id_or_prefix: str) -> RunRecord:
        return self.delegate.get_run(run_id_or_prefix)

    def list_steps(self, run_id: str) -> tuple[StepRecord, ...]:
        return self.delegate.list_steps(run_id)

    def list_artifacts(self, run_id: str) -> tuple[ArtifactRecord, ...]:
        return self.delegate.list_artifacts(run_id)

    def list_events(self, run_id: str) -> tuple[EventRecord, ...]:
        return self.delegate.list_events(run_id)

    def list_validations(self, run_id: str) -> tuple[ValidationRecord, ...]:
        return self.delegate.list_validations(run_id)

    def list_publications(self, run_id: str) -> tuple[PublicationRecord, ...]:
        return self.delegate.list_publications(run_id)


class DiffReportsRuntimeTests(unittest.TestCase):
    def test_diff_report_metadata_events_manifest_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(DiffJob())

            self.assertTrue(result.succeeded, result.error)
            run_root = workspace / "runs" / "demo" / "diff_reports" / result.run_id
            report_path = run_root / "reports" / "diff.json"
            self.assertTrue(report_path.is_file())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["report_version"], "1")
            self.assertEqual(payload["kind"], "diff")
            self.assertEqual(
                payload["summary"],
                {"added": 1, "removed": 1, "changed": 1, "unchanged": 0},
            )
            self.assertEqual(payload["dataset_id"], "demo.diff_reports")
            serialized = json.dumps(payload)
            for secret in ("old-secret", "new-secret", "keep-secret", "another-secret"):
                self.assertNotIn(secret, serialized)
            self.assertIn("[REDACTED]", serialized)

            manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn(
                {"kind": "diff", "path": "reports/diff.json", "step": "ProduceDiff"},
                manifest["reports"],
            )

            rows = store.list_dataset_diffs(result.run_id)
            self.assertEqual(len(rows), 1)
            diff = rows[0]
            self.assertEqual((diff.added_count, diff.removed_count, diff.changed_count), (1, 1, 1))
            self.assertEqual(diff.report_path, "reports/diff.json")
            self.assertTrue(diff.previous_version_id.startswith("sha256-"))
            self.assertTrue(diff.candidate_fingerprint.startswith("sha256-"))

            event_types = {event.event_type for event in store.list_events(result.run_id)}
            self.assertTrue(
                {"DIFF_STARTED", "DIFF_COMPLETED", "DIFF_REPORT_WRITTEN"}.issubset(event_types)
            )

            cli_runner = CliRunner()
            with cli_runner.isolated_filesystem(temp_dir=tmp):
                status_result = cli_runner.invoke(
                    app,
                    ["status", result.run_id[:8], "--workspace", str(workspace), "--json"],
                )
            self.assertEqual(status_result.exit_code, 0, status_result.output)
            status_payload = json.loads(status_result.stdout)
            self.assertEqual(status_payload["diffs"][0]["changed_count"], 1)
            self.assertEqual(status_payload["diffs"][0]["report_path"], "reports/diff.json")

    def test_legacy_metadata_store_without_diff_capability_still_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            delegate = SQLiteMetadataStore.for_workspace(workspace)
            legacy = LegacyMetadataStore(delegate)
            result = Runner(LocalArtifactStore(workspace), metadata_store=legacy).run(DiffJob())
            self.assertTrue(result.succeeded, result.error)
            run_root = workspace / "runs" / "demo" / "diff_reports" / result.run_id
            self.assertTrue((run_root / "reports" / "diff.json").is_file())


if __name__ == "__main__":
    unittest.main()
