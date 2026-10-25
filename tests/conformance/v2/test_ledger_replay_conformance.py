from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.domain.replay import ReplayLineage
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.ports.replay import ReplayLineageLedger

_NOW = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")


def make_lineage(
    *,
    dataset_id: str | None = None,
    source_run_id: IngestionRunId | None = None,
    replay_run_id: IngestionRunId | None = None,
    replayed_at: datetime | None = None,
    published: bool = False,
    checksum: str = "sha256-abc123def456",
) -> ReplayLineage:
    source = source_run_id or IngestionRunId.new()
    replay = replay_run_id or IngestionRunId.new()
    return ReplayLineage(
        source_run_id=source,
        replay_run_id=replay,
        dataset_id=dataset_id or f"test.dataset.{uuid4().hex[:6]}",
        version_id=f"sha256-v-{uuid4().hex[:8]}",
        origin_raw_checksum=checksum,
        replay_raw_checksum=checksum,
        matched=True,
        replayed_at=replayed_at or _NOW,
        published=published,
    )


def exercise_replay_lineage_ledger(ledger: ReplayLineageLedger) -> None:
    assert isinstance(ledger, ReplayLineageLedger)

    # 1. Record lineage
    dataset_a = f"test.dataset.{uuid4().hex[:6]}"
    source_run = IngestionRunId.new()
    lineage1 = make_lineage(
        dataset_id=dataset_a,
        source_run_id=source_run,
        replayed_at=_NOW,
        published=False,
    )

    recorded = ledger.record_replay_lineage(lineage1)
    assert recorded == lineage1

    # 2. Idempotent re-record
    re_recorded = ledger.record_replay_lineage(lineage1)
    assert re_recorded == lineage1

    # 3. Conflict rejection on reused lineage_id
    conflicting = ReplayLineage(
        lineage_id=lineage1.lineage_id,
        source_run_id=IngestionRunId.new(),
        replay_run_id=IngestionRunId.new(),
        dataset_id=dataset_a,
        version_id="sha256-diff",
        origin_raw_checksum="sha256-diff",
        replay_raw_checksum="sha256-diff",
        matched=False,
        replayed_at=_NOW,
    )
    with pytest.raises(ValueError, match="Replay lineage ID cannot be reused"):
        ledger.record_replay_lineage(conflicting)

    # 4. Publication promotion
    promoted = replace(lineage1, published=True)
    res_promoted = ledger.record_replay_lineage(promoted)
    assert res_promoted.published is True

    # 5. Multiple records & query filtering
    lineage2 = make_lineage(
        dataset_id=dataset_a,
        replayed_at=_NOW + timedelta(seconds=10),
    )
    ledger.record_replay_lineage(lineage2)

    dataset_b = f"test.dataset.{uuid4().hex[:6]}"
    lineage3 = make_lineage(
        dataset_id=dataset_b,
        replayed_at=_NOW + timedelta(seconds=20),
    )
    ledger.record_replay_lineage(lineage3)

    # Query all
    all_replays = ledger.list_replays()
    assert lineage1 in all_replays or promoted in all_replays
    assert lineage2 in all_replays
    assert lineage3 in all_replays

    # Query by dataset
    replays_a = ledger.list_replays(dataset_id=dataset_a)
    assert len(replays_a) == 2
    assert replays_a[0].lineage_id == lineage1.lineage_id
    assert replays_a[0].published is True
    assert replays_a[1].lineage_id == lineage2.lineage_id

    # Query by source_run_id
    replays_source = ledger.list_replays(source_run_id=source_run)
    assert len(replays_source) == 1
    assert replays_source[0].source_run_id == source_run

    # Query non-existent
    assert ledger.list_replays(dataset_id="non.existent.dataset") == ()


def test_memory_ledger_replay_conformance() -> None:
    ledger = MemoryPublicationLedger()
    exercise_replay_lineage_ledger(ledger)


@pytest.mark.skipif(
    not POSTGRES_DSN, reason="PYINGEST_TEST_POSTGRES_DSN is required for postgres ledger test"
)
def test_postgres_ledger_replay_conformance() -> None:
    from pyingestkit.adapters.postgres import PostgresPublicationLedger

    assert POSTGRES_DSN is not None
    ledger = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        exercise_replay_lineage_ledger(ledger)
    finally:
        ledger.close()
