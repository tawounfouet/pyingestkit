from __future__ import annotations

import multiprocessing
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty

from pyingestkit.adapters.filesystem import (
    FileConditionalDatasetPublisher,
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
)
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance import (
    PublicationIntent,
    PublicationOperationId,
    PublicationRevision,
)

_DATASET_ID = "governance.process_race"
_REQUESTED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _put_version(
    store: FileDatasetVersionStore,
    workspace: Path,
    name: str,
    value: str,
):
    source = workspace / f"{name}.csv"
    source.write_text(f"id,value\n1,{value}\n", encoding="utf-8")
    run_id = IngestionRunId.new()
    version = FileCsvDatasetVersionMaterializerV2(allowed_roots=(workspace,)).materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id=_DATASET_ID,
            resource=ResourceReference(
                namespace="governance.process",
                resource_id=name,
                locator=source.resolve().as_uri(),
                media_type="text/csv",
                format="csv",
            ),
            ingestion_run_id=run_id,
            created_at=_REQUESTED_AT,
        )
    )
    return store.put(version)


def _intent(reference, expected: PublicationRevision) -> PublicationIntent:
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=expected,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=_REQUESTED_AT,
    )


def _publish_worker(root: str, intent: PublicationIntent, queue) -> None:
    store = FileDatasetVersionStore(root=Path(root))
    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
    )
    outcome = publisher.compare_and_publish(intent)
    queue.put(outcome.status.value)


def _race(
    root: Path,
    first: PublicationIntent,
    second: PublicationIntent,
) -> list[str]:
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [
        context.Process(
            target=_publish_worker,
            args=(str(root), intent, queue),
        )
        for intent in (first, second)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(20)
        assert process.exitcode == 0

    values: list[str] = []
    for _ in processes:
        try:
            values.append(queue.get(timeout=5))
        except Empty as exc:
            raise AssertionError("CAS worker did not report an outcome") from exc
    return sorted(values)


def test_initial_publication_process_race_has_exactly_one_winner(
    tmp_path: Path,
) -> None:
    root = tmp_path / "versions"
    store = FileDatasetVersionStore(root=root)
    first = _put_version(store, tmp_path, "initial-a", "a")
    second = _put_version(store, tmp_path, "initial-b", "b")

    outcomes = _race(
        root,
        _intent(first, PublicationRevision.initial()),
        _intent(second, PublicationRevision.initial()),
    )

    assert outcomes == ["conflict", "succeeded"]


def test_existing_revision_process_race_has_exactly_one_winner(
    tmp_path: Path,
) -> None:
    root = tmp_path / "versions"
    store = FileDatasetVersionStore(root=root)
    baseline = _put_version(store, tmp_path, "baseline", "zero")
    first = _put_version(store, tmp_path, "race-a", "a")
    second = _put_version(store, tmp_path, "race-b", "b")

    initial_publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
    )
    committed = initial_publisher.compare_and_publish(
        _intent(baseline, PublicationRevision.initial())
    )
    assert committed.snapshot is not None

    outcomes = _race(
        root,
        _intent(first, committed.snapshot.revision),
        _intent(second, committed.snapshot.revision),
    )

    assert outcomes == ["conflict", "succeeded"]


def _holding_publish_worker(root: str, intent: PublicationIntent, ready, release, queue) -> None:
    store = FileDatasetVersionStore(root=Path(root))

    def hold_lock(phase: str) -> None:
        if phase == "before_replace":
            ready.set()
            if not release.wait(timeout=15):
                raise OSError("lock holder timed out waiting for release")

    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
        fault_injector=hold_lock,
    )
    outcome = publisher.compare_and_publish(intent)
    queue.put(\n        (outcome.status.value, None if outcome.failure is None else outcome.failure.error_code)\n    )


def _timeout_publish_worker(root: str, intent: PublicationIntent, queue) -> None:
    store = FileDatasetVersionStore(root=Path(root))
    publisher = FileConditionalDatasetPublisher(
        store=store,
        ledger=MemoryPublicationLedger(),
        lock_timeout_seconds=0.05,
    )
    outcome = publisher.compare_and_publish(intent)
    queue.put(\n        (outcome.status.value, None if outcome.failure is None else outcome.failure.error_code)\n    )


def test_process_lock_acquisition_timeout_fails_before_pointer_side_effect(
    tmp_path: Path,
) -> None:
    root = tmp_path / "versions"
    store = FileDatasetVersionStore(root=root)
    first = _put_version(store, tmp_path, "lock-holder", "a")
    second = _put_version(store, tmp_path, "lock-timeout", "b")
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    release = context.Event()
    holder_queue = context.Queue()
    timeout_queue = context.Queue()

    holder = context.Process(
        target=_holding_publish_worker,
        args=(
            str(root),
            _intent(first, PublicationRevision.initial()),
            ready,
            release,
            holder_queue,
        ),
    )
    holder.start()
    assert ready.wait(timeout=10)

    contender = context.Process(
        target=_timeout_publish_worker,
        args=(
            str(root),
            _intent(second, PublicationRevision.initial()),
            timeout_queue,
        ),
    )
    contender.start()
    contender.join(10)
    assert contender.exitcode == 0
    assert timeout_queue.get(timeout=5) == (
        "failed",
        "governance.filesystem.lock_timeout",
    )

    release.set()
    holder.join(10)
    assert holder.exitcode == 0
    assert holder_queue.get(timeout=5)[0] == "succeeded"

    published = store.get_published(_DATASET_ID)
    assert published is not None
    assert published.version.identity == first.identity
