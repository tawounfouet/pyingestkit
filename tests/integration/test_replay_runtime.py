from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pyingestkit import Dataset, FilesystemDatasetVersionStore, Job, Pipeline, Runner, Step
from pyingestkit.artifacts import LocalArtifactStore
from pyingestkit.core.context import RunContext
from pyingestkit.core.exceptions import ReplayMismatchError
from pyingestkit.core.registry import JobRegistry
from pyingestkit.metadata import SQLiteMetadataStore
from pyingestkit.parsers import JsonParser
from pyingestkit.replay import ReplayService
from pyingestkit.sources.http import HttpResponse, HttpSource
from pyingestkit.sources.local import LocalSource


class _StaticClient:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.calls = 0

    def send(self, request):
        self.calls += 1
        return HttpResponse(
            status_code=200,
            url=request.url,
            headers={"content-type": "application/json"},
            content=self.content,
        )


class _BombClient:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, request):
        self.calls += 1
        raise AssertionError("network must not be called during replay")


class _FetchHttp(Step):
    step_name = "FetchHttp"

    def __init__(self, job):
        self.job = job

    def execute(self, context: RunContext, data):
        return HttpSource("https://example.test/data.json", client=self.job.client).fetch(context)


class _ParseJson(Step):
    step_name = "ParseJson"

    def __init__(self, job):
        self.job = job

    def execute(self, context: RunContext, data):
        dataset = JsonParser().parse(data)
        if self.job.mutate:
            return Dataset(
                [{**dict(row), "name": "MUTATED"} for row in dataset],
                fields=dataset.fields,
                source_artifact_id=dataset.source_artifact_id,
            )
        return dataset


class _HttpJob(Job):
    id = "demo.replay_http"
    version = "1.0.0"

    def __init__(self, client):
        self.client = client
        self.mutate = False

    def pipeline(self):
        return Pipeline([_FetchHttp(self), _ParseJson(self)])


class _FetchLocal(Step):
    step_name = "FetchLocal"

    def __init__(self, path):
        self.path = path

    def execute(self, context: RunContext, data):
        return LocalSource(self.path).fetch(context)


class _LocalToDataset(Step):
    step_name = "ToDataset"

    def execute(self, context: RunContext, data):
        text = Path(data.path).read_text(encoding="utf-8")
        return Dataset([{"text": text}], source_artifact_id=data.artifact_id)


class _LocalJob(Job):
    id = "demo.replay_local"
    version = "1.0.0"

    def __init__(self, path):
        self.path = path

    def pipeline(self):
        return Pipeline([_FetchLocal(self.path), _LocalToDataset()])


class ReplayRuntimeTests(unittest.TestCase):
    def _version_source(self, workspace, metadata, result, dataset, job):
        raw = metadata.list_artifacts(result.run_id)[0]
        return FilesystemDatasetVersionStore(workspace, metadata_store=metadata).create_version(
            dataset,
            dataset_id=job.id,
            created_from_run_id=result.run_id,
            job_id=job.id,
            job_version=job.version,
            source_artifact_id=raw.artifact_id,
            source_raw_sha256=raw.sha256,
        )

    def test_http_replay_makes_zero_network_call_and_verifies_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            client = _StaticClient(b'[{"id":1,"name":"A"}]')
            job = _HttpJob(client)
            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            source = runner.run(job)
            dataset = source.steps[-1].output
            self._version_source(workspace, metadata, source, dataset, job)
            bomb = _BombClient()
            job.client = bomb
            registry = JobRegistry()
            registry.register(job)
            replay = ReplayService(runner, registry).replay(source.run_id)
            self.assertTrue(replay.succeeded)
            self.assertTrue(replay.matched)
            self.assertEqual(bomb.calls, 0)
            raw = metadata.list_artifacts(replay.run.run_id)[0]
            origin = metadata.list_artifacts(source.run_id)[0]
            self.assertEqual(raw.sha256, origin.sha256)
            events = {row.event_type for row in metadata.list_events(replay.run.run_id)}
            self.assertIn("RAW_REPLAYED", events)
            self.assertIn("REPLAY_VERIFICATION_COMPLETED", events)
            manifest = json.loads(
                (
                    workspace
                    / "runs"
                    / "demo"
                    / "replay_http"
                    / replay.run.run_id
                    / "manifest.json"
                ).read_text()
            )
            self.assertEqual(manifest["replay"]["source_run_id"], source.run_id)
            self.assertTrue(manifest["replay"]["matched"])

    def test_local_replay_survives_source_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            path = Path(tmp) / "source.txt"
            path.write_text("original")
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            job = _LocalJob(path)
            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            source = runner.run(job)
            self._version_source(workspace, metadata, source, source.steps[-1].output, job)
            path.unlink()
            registry = JobRegistry()
            registry.register(job)
            replay = ReplayService(runner, registry).replay(source.run_id)
            self.assertEqual(replay.run.steps[-1].output.to_rows(), [{"text": "original"}])
            self.assertTrue(replay.matched)

    def test_same_version_mismatch_is_detected_after_artifacts_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            job = _HttpJob(_StaticClient(b'[{"id":1,"name":"A"}]'))
            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            source = runner.run(job)
            self._version_source(workspace, metadata, source, source.steps[-1].output, job)
            job.client = _BombClient()
            job.mutate = True
            registry = JobRegistry()
            registry.register(job)
            with self.assertRaises(ReplayMismatchError) as caught:
                ReplayService(runner, registry).replay(source.run_id)
            replay_run_id = caught.exception.run_id
            self.assertIsNotNone(replay_run_id)
            self.assertEqual(len(metadata.list_artifacts(replay_run_id)), 1)
            self.assertEqual(metadata.get_replay_run(replay_run_id).status, "MISMATCH")  # type: ignore[union-attr]

    def test_replay_never_falls_back_to_live_source_when_raw_does_not_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            job = _HttpJob(_StaticClient(b'[{"id":1,"name":"A"}]'))
            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            source = runner.run(job)
            bomb = _BombClient()
            job.client = bomb

            # Change the source identity while deliberately keeping the same job version.
            class _ChangedFetch(Step):
                step_name = "FetchHttp"

                def execute(self, context: RunContext, data):
                    return HttpSource("https://example.test/other.json", client=bomb).fetch(context)

            job.pipeline = lambda: Pipeline([_ChangedFetch(), _ParseJson(job)])  # type: ignore[method-assign]
            registry = JobRegistry()
            registry.register(job)
            replay = ReplayService(runner, registry).replay(source.run_id, verify=False)
            self.assertFalse(replay.run.succeeded)
            self.assertEqual(bomb.calls, 0)
            self.assertIn("ReplayError", replay.run.error or "")

    def test_allow_version_change_records_compare_mode_without_strict_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            metadata = SQLiteMetadataStore.for_workspace(workspace)
            job = _HttpJob(_StaticClient(b'[{"id":1,"name":"A"}]'))
            runner = Runner(LocalArtifactStore(workspace), metadata_store=metadata)
            source = runner.run(job)
            self._version_source(workspace, metadata, source, source.steps[-1].output, job)
            job.client = _BombClient()
            job.version = "2.0.0"
            job.mutate = True
            registry = JobRegistry()
            registry.register(job)
            replay = ReplayService(runner, registry).replay(
                source.run_id, allow_version_change=True
            )
            self.assertEqual(replay.verification_mode, "COMPARE")
            self.assertFalse(replay.matched)
            self.assertTrue(replay.run.succeeded)
