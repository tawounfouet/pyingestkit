from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.application.replay import ReplayServiceV2
from pyingestkit.application.resolver import (
    DefaultReplayProvenanceResolver,
    sanitize_parameter_overrides,
)
from pyingestkit.application.runtime import IngestionRuntime
from pyingestkit.decoders import JsonDecoder
from pyingestkit.domain.artifacts import (
    ArtifactKind,
    ArtifactReference,
    ArtifactRetention,
    PutArtifactRequest,
)
from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    ConditionalPublicationStatus,
    PublicationRevision,
    PublicationSnapshot,
)
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.replay import ReplayLineage, ReplayRequest
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.sources import Source
from pyingestkit.stores import FileArtifactStore, FileDatasetVersionStore

_NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)


def _raw_artifact(run_id: IngestionRunId, checksum: str = "sha256-abc") -> ArtifactReference:
    return ArtifactReference(
        artifact_id=f"raw-{uuid4().hex[:8]}",
        kind="raw",
        resource=ResourceReference(
            namespace="pyingestkit.test",
            resource_id="raw-1",
            locator="memory://artifacts/raw-1",
        ),
        checksum_algorithm="sha256",
        checksum=checksum,
    )


def test_replay_lineage_validation() -> None:
    source_run = IngestionRunId.new()
    replay_run = IngestionRunId.new()

    lineage = ReplayLineage(
        source_run_id=source_run,
        replay_run_id=replay_run,
        dataset_id="test.dataset",
        version_id="sha256-version",
        origin_raw_checksum="sha256-raw",
        replay_raw_checksum="sha256-raw",
        matched=True,
        replayed_at=_NOW,
    )
    assert lineage.source_run_id == source_run
    assert lineage.replay_run_id == replay_run
    assert lineage.matched is True
    assert lineage.published is False
    assert lineage.lineage_id is not None

    with pytest.raises(ValueError, match="replay_run_id != source_run_id"):
        ReplayLineage(
            source_run_id=source_run,
            replay_run_id=source_run,
            dataset_id="test.dataset",
            version_id="sha256-version",
            origin_raw_checksum="sha256-raw",
            replay_raw_checksum="sha256-raw",
            matched=True,
            replayed_at=_NOW,
        )

    with pytest.raises(ValueError, match="must match"):
        ReplayLineage(
            source_run_id=source_run,
            replay_run_id=replay_run,
            dataset_id="test.dataset",
            version_id="sha256-version",
            origin_raw_checksum="sha256-raw-1",
            replay_raw_checksum="sha256-raw-2",
            matched=True,
            replayed_at=_NOW,
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        ReplayLineage(
            source_run_id=source_run,
            replay_run_id=replay_run,
            dataset_id="test.dataset",
            version_id="sha256-version",
            origin_raw_checksum="sha256-raw",
            replay_raw_checksum="sha256-raw",
            matched=True,
            replayed_at=datetime(2026, 10, 25, 8, 0),
        )


def test_sanitize_parameter_overrides() -> None:
    params = {
        "batch_size": 100,
        "api_key": "super-secret-token",
        "auth_password": "mypassword",
        "target_env": "production",
    }
    sanitized = sanitize_parameter_overrides(params)
    assert sanitized["batch_size"] == "100"
    assert sanitized["target_env"] == "production"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["auth_password"] == "[REDACTED]"


def test_resolver_from_version_reconstructs_replay_request(tmp_path: Path) -> None:
    version_store = FileDatasetVersionStore(root=tmp_path / "versions")
    artifact_store = FileArtifactStore(root=tmp_path / "artifacts")
    source_run_id = IngestionRunId.new()
    raw = _raw_artifact(source_run_id, checksum="sha256-" + "a" * 64)

    definition = IngestionDefinition(
        name="test.raw.def",
        source=Source.file(path="/data/test.json"),
        decoder="json",
        dataset="test.dataset",
    )

    version_ref = DatasetVersionReference(
        dataset_id="test.dataset",
        version_id="sha256-" + "v" * 64,
        created_at=_NOW,
        schema_fingerprint="schema-fp",
        content_fingerprint="sha256-" + "v" * 64,
        artifact_reference=raw,
        metadata=(
            ("source_run_id", str(source_run_id)),
            ("definition_name", definition.name),
        ),
    )

    class _DummyVersionStore:
        def get(self, dataset_id: str, version_id: str) -> DatasetVersionReference:
            if dataset_id == "test.dataset" and version_id == version_ref.version_id:
                return version_ref
            raise KeyError(version_id)

        def put(self, version: object) -> DatasetVersionReference:
            raise NotImplementedError

        def list(self, dataset_id: str) -> tuple[DatasetVersionReference, ...]:
            return (version_ref,)

        def read(self, reference: object) -> object:
            raise NotImplementedError

    version_store = _DummyVersionStore()

    resolver = DefaultReplayProvenanceResolver(
        version_store=version_store,  # type: ignore[arg-type]
        artifact_store=artifact_store,
        definitions={definition.name: definition},
    )

    request = resolver.resolve_from_version(
        "test.dataset",
        version_ref.version_id,
        parameter_overrides={"batch_size": 50},
    )

    assert request.source_run_id == source_run_id
    assert request.origin_raw_artifact == raw
    assert request.expected_dataset_version == version_ref
    assert dict(request.definition.options).get("batch_size") == "50"


def test_resolver_from_run_reconstructs_replay_request(tmp_path: Path) -> None:
    version_store = FileDatasetVersionStore(root=tmp_path / "versions")
    artifact_store = FileArtifactStore(root=tmp_path / "artifacts")
    source_run_id = IngestionRunId.new()
    raw = _raw_artifact(source_run_id, checksum="sha256-" + "b" * 64)

    definition = IngestionDefinition(
        name="test.run.def",
        source=Source.file(path="/data/test.json"),
        decoder="json",
        dataset="test.dataset",
    )

    resolver = DefaultReplayProvenanceResolver(
        version_store=version_store,
        artifact_store=artifact_store,
    )
    resolver.register_run(source_run_id, definition, raw)

    request = resolver.resolve_from_run(source_run_id)
    assert request.source_run_id == source_run_id
    assert request.origin_raw_artifact == raw
    assert request.definition.name == definition.name


class _DummyConditionalPublisher:
    def __init__(self, dataset_id: str) -> None:
        self.dataset_id = dataset_id
        self.intents: list[object] = []

    def inspect(self, dataset_id: str) -> PublicationSnapshot:
        return PublicationSnapshot(
            dataset_id=dataset_id,
            revision=PublicationRevision.initial(),
        )

    def compare_and_publish(self, intent: object) -> object:
        from pyingestkit.domain.datasets.publication import PublishedDataset
        from pyingestkit.domain.governance import (
            ConditionalPublicationOutcome,
            ConditionalPublicationStatus,
        )

        self.intents.append(intent)
        published_version = intent.dataset_version
        return ConditionalPublicationOutcome(
            intent=intent,  # type: ignore[arg-type]
            status=ConditionalPublicationStatus.SUCCEEDED,
            completed_at=_NOW,
            snapshot=PublicationSnapshot(
                dataset_id=self.dataset_id,
                revision=PublicationRevision.new(),
                published_dataset=PublishedDataset(
                    dataset_id=self.dataset_id,
                    version=published_version,
                    published_at=_NOW,
                    published_from_run_id=intent.ingestion_run_id,
                ),
            ),
        )


def test_replay_service_executes_records_lineage_and_publishes_cas(tmp_path: Path) -> None:
    from pyingestkit.application.decoders import DecoderRegistry
    from pyingestkit.application.sources import SourceRegistry

    artifact_store = FileArtifactStore(root=tmp_path / "artifacts")
    version_store = FileDatasetVersionStore(root=tmp_path / "versions")
    ledger = MemoryPublicationLedger()

    decoders = DecoderRegistry()
    decoders.register(JsonDecoder())
    runtime = IngestionRuntime(
        sources=SourceRegistry(),
        decoders=decoders,
        artifacts=artifact_store,
        versions=version_store,
        publisher=version_store,
        clock=lambda: _NOW,
    )
    service = ReplayServiceV2(
        runtime=runtime,
        ledger=ledger,
        clock=lambda: _NOW,
    )

    source_run_id = IngestionRunId.new()
    raw_content = b'{"records": [{"id": 1, "name": "Ada"}]}'

    raw_put = artifact_store.put(
        PutArtifactRequest(
            ingestion_run_id=source_run_id,
            correlation=CorrelationContext(ingestion_run_id=str(source_run_id)),
            kind=ArtifactKind.RAW,
            name="origin.raw",
            content=raw_content,
            source_resource=ResourceReference(
                namespace="pyingestkit.test",
                resource_id="raw-1",
                locator="file:///data/test.json",
            ),
            source_acquired_at=_NOW,
            media_type="application/json",
            retention=ArtifactRetention(retain=True),
        )
    )
    assert raw_put.reference is not None

    definition = IngestionDefinition(
        name="test.replay.pub",
        source=Source.file(path="/data/test.json"),
        decoder="json",
        dataset="test.dataset",
    )

    request = ReplayRequest(
        source_run_id=source_run_id,
        definition=definition,
        origin_raw_artifact=raw_put.reference,
    )

    result = service.replay(request)
    assert result.succeeded
    assert result.lineage is not None
    assert result.lineage.source_run_id == source_run_id
    assert result.lineage.replay_run_id == result.replay_run_id
    assert result.lineage.published is False

    replays = ledger.list_replays(dataset_id="test.dataset")
    assert len(replays) == 1
    assert replays[0].source_run_id == source_run_id
    assert replays[0].published is False

    publisher = _DummyConditionalPublisher("test.dataset")
    outcome = service.publish_replay(result, publisher=publisher)  # type: ignore[arg-type]
    assert outcome.status is ConditionalPublicationStatus.SUCCEEDED

    replays_after = ledger.list_replays(dataset_id="test.dataset")
    assert len(replays_after) == 1
    assert replays_after[0].published is True
