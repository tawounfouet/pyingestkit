from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from pyingestkit.adapters.filesystem import (
    FileConditionalDatasetPublisher,
    FileCsvDatasetVersionMaterializerV2,
    FileDatasetVersionStore,
)
from pyingestkit.adapters.postgres import PostgresPublicationLedger
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.domain.governance import (
    ConditionalPublicationStatus,
    PublicationIntent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.governance.rollback import GovernedRollbackService

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not POSTGRES_DSN,
    reason="PostgreSQL is required for durable LOT-28 rollback evidence",
)

_NOW = datetime(2026, 10, 4, 4, 0, tzinfo=UTC)


def _put_version(
    store: FileDatasetVersionStore,
    workspace: Path,
    *,
    dataset_id: str,
    name: str,
    value: str,
):
    source = workspace / f"{name}.csv"
    source.write_text(f"id,value\n1,{value}\n", encoding="utf-8")
    run_id = IngestionRunId.new()
    version = FileCsvDatasetVersionMaterializerV2(
        allowed_roots=(workspace,),
    ).materialize(
        ResourceDatasetVersionRequestV2(
            dataset_id=dataset_id,
            resource=ResourceReference(
                namespace="rollback.postgres",
                resource_id=name,
                locator=source.resolve().as_uri(),
                media_type="text/csv",
                format="csv",
            ),
            ingestion_run_id=run_id,
            created_at=_NOW,
        )
    )
    return store.put(version)


def _intent(reference, revision, when):
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=PublicationOperationId.new(),
        dataset_version=reference,
        expected_revision=revision,
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        requested_at=when,
    )


def test_postgres_rollback_evidence_survives_ledger_restart(tmp_path: Path) -> None:
    assert POSTGRES_DSN is not None
    dataset_id = f"rollback.postgres.{uuid4().hex}"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = FileDatasetVersionStore(root=tmp_path / "versions")
    v1 = _put_version(
        store,
        workspace,
        dataset_id=dataset_id,
        name="v1",
        value="one",
    )
    v2 = _put_version(
        store,
        workspace,
        dataset_id=dataset_id,
        name="v2",
        value="two",
    )

    ledger = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        publisher = FileConditionalDatasetPublisher(
            store=store,
            ledger=ledger,
            clock=lambda: _NOW + timedelta(seconds=1),
        )
        first = publisher.compare_and_publish(_intent(v1, PublicationRevision.initial(), _NOW))
        assert first.snapshot is not None
        current = publisher.compare_and_publish(_intent(v2, first.snapshot.revision, _NOW))
        assert current.snapshot is not None

        intent = _intent(
            v1,
            current.snapshot.revision,
            _NOW + timedelta(seconds=2),
        )
        outcome = GovernedRollbackService(
            store=store,
            publisher=FileConditionalDatasetPublisher(
                store=store,
                ledger=ledger,
                clock=lambda: _NOW + timedelta(seconds=3),
            ),
            ledger=ledger,
            clock=lambda: _NOW + timedelta(seconds=2),
        ).rollback(intent)

        assert outcome.status is ConditionalPublicationStatus.SUCCEEDED
        assert outcome.snapshot is not None
        rollback_revision = outcome.snapshot.revision
        assert ledger.list_unresolved(dataset_id) == ()
    finally:
        ledger.close()

    restarted = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        persisted = restarted.get_operation(intent.operation_id)
        assert persisted is not None
        persisted.assert_same_intent_as(intent)
        events = restarted.list_events(intent.operation_id)
        assert [event.event_type for event in events] == [
            PublicationLifecycleEventType.ROLLBACK_REQUESTED,
            PublicationLifecycleEventType.ROLLBACK_COMMITTED,
        ]
        assert events[-1].next_revision == rollback_revision
        assert restarted.list_unresolved(dataset_id) == ()
    finally:
        restarted.close()
