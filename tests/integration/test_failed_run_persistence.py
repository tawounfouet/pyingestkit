from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit import Job, Pipeline, RunContext, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.events import EventType, HookPolicy
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.runtime import Runner
from pyingestkit.core.events import EventBus


class Explode(Step):
    def execute(self, context: RunContext, data):
        raise RuntimeError("boom")


class Demo(Job):
    id = "demo.failed"
    def pipeline(self) -> Pipeline:
        return Pipeline([Explode()])


class FailedRunPersistenceTests(unittest.TestCase):
    def test_failed_step_is_persisted_and_manifest_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            result = Runner(LocalArtifactStore(workspace), metadata_store=store).run(Demo())
            self.assertFalse(result.succeeded)
            self.assertEqual(store.get_run(result.run_id).status, "FAILED")
            self.assertEqual(store.list_steps(result.run_id)[0].status, "FAILED")
            manifest = json.loads(next(workspace.rglob("manifest.json")).read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "FAILED")

    def test_critical_run_started_hook_becomes_failed_run_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            bus = EventBus()
            bus.subscribe(
                EventType.RUN_STARTED,
                lambda event: (_ for _ in ()).throw(RuntimeError("hook boom")),
                policy=HookPolicy.CRITICAL,
            )
            result = Runner(LocalArtifactStore(workspace), metadata_store=store, events=bus).run(Demo())
            self.assertFalse(result.succeeded)
            self.assertIn("HookError", result.error or "")
            self.assertEqual(store.get_run(result.run_id).status, "FAILED")
            self.assertTrue(next(workspace.rglob("manifest.json")).exists())

    def test_critical_step_succeeded_hook_replaces_success_with_single_failed_step(self) -> None:
        class Pass(Step):
            def execute(self, context: RunContext, data):
                return data

        class PassingJob(Job):
            id = "demo.hook_after_step"
            def pipeline(self) -> Pipeline:
                return Pipeline([Pass()])

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / ".pyingest"
            store = SQLiteMetadataStore.for_workspace(workspace)
            bus = EventBus()
            bus.subscribe(
                EventType.STEP_SUCCEEDED,
                lambda event: (_ for _ in ()).throw(RuntimeError("post-step hook boom")),
                policy=HookPolicy.CRITICAL,
            )
            result = Runner(LocalArtifactStore(workspace), metadata_store=store, events=bus).run(PassingJob())
            self.assertFalse(result.succeeded)
            self.assertEqual(len(result.steps), 1)
            self.assertEqual(result.steps[0].status.value, "FAILED")
            self.assertEqual(len(store.list_steps(result.run_id)), 1)
            self.assertEqual(store.list_steps(result.run_id)[0].status, "FAILED")


if __name__ == "__main__":
    unittest.main()
