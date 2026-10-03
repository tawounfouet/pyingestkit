from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

import pytest

from pyingestkit.domain.datasets import DatasetVersionReference
from pyingestkit.domain.governance import (
    PublicationIntent,
    PublicationLifecycleEvent,
    PublicationLifecycleEventType,
    PublicationOperationId,
    PublicationRevision,
)
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.ports.governance import PublicationLedger

_NOW = datetime(2026, 10, 3, 21, 0, tzinfo=UTC)


class InspectablePublicationLedger(PublicationLedger, Protocol):
    def list_events(
        self,
        operation_id: PublicationOperationId | None = None,
        *,
        dataset_id: str | None = None,
    ) -> tuple[PublicationLifecycleEvent, ...]: ...


def make_intent(
    *,
    dataset_id: str | None = None,
    operation_id: PublicationOperationId | None = None,
    version_id: str | None = None,
) -> PublicationIntent:
    resolved_dataset_id = dataset_id or f"conformance.dataset.{uuid4().hex}"
    run_id = IngestionRunId.new()
    return PublicationIntent(
        operation_id=operation_id or PublicationOperationId.new(),
        dataset_version=DatasetVersionReference(
            dataset_id=resolved_dataset_id,
            version_id=version_id or f"sha256-{'a' * 64}",
            created_at=_NOW,
            schema_fingerprint="schema-conformance",
            content_fingerprint=version_id or f"sha256-{'a' * 64}",
            metadata=(("source", "ledger-conformance"),),
        ),
        expected_revision=PublicationRevision.initial(),
        ingestion_run_id=run_id,
        correlation=CorrelationContext(
            ingestion_run_id=str(run_id),
            trace_id=f"trace-{uuid4().hex}",
        ),
        requested_at=_NOW,
    )


def make_event(
    intent: PublicationIntent,
    event_type: PublicationLifecycleEventType,
    *,
    event_id: str | None = None,
) -> PublicationLifecycleEvent:
    return PublicationLifecycleEvent(
        event_id=event_id or f"event-{uuid4().hex}",
        event_type=event_type,
        dataset_id=intent.dataset_id,
        occurred_at=_NOW,
        operation_id=intent.operation_id,
        dataset_version=intent.dataset_version,
        previous_revision=intent.expected_revision,
        next_revision=(
            PublicationRevision.new()
            if event_type is PublicationLifecycleEventType.PUBLICATION_COMMITTED
            else None
        ),
        metadata=(("evidence", "conformance"),),
    )


def exercise_publication_ledger(ledger: InspectablePublicationLedger) -> None:
    assert isinstance(ledger, PublicationLedger)

    intent = make_intent()
    requested = make_event(
        intent,
        PublicationLifecycleEventType.PUBLICATION_REQUESTED,
    )
    terminal = make_event(
        intent,
        PublicationLifecycleEventType.PUBLICATION_COMMITTED,
    )

    assert ledger.register(intent) == intent
    assert ledger.register(intent) == intent
    assert ledger.get_operation(intent.operation_id) == intent
    assert ledger.list_operations(intent.dataset_id) == (intent,)
    assert ledger.list_unresolved(intent.dataset_id) == (intent,)

    ledger.append(requested)
    ledger.append(requested)
    assert ledger.list_events(intent.operation_id) == (requested,)
    assert ledger.list_unresolved(intent.dataset_id) == (intent,)

    ledger.append(terminal)
    assert ledger.list_events(intent.operation_id) == (requested, terminal)
    assert ledger.list_unresolved(intent.dataset_id) == ()

    with pytest.raises(ValueError, match="Resolved publication operation"):
        ledger.append(
            make_event(
                intent,
                PublicationLifecycleEventType.VERSION_OBSERVED,
            )
        )

    changed = make_intent(
        dataset_id=intent.dataset_id,
        operation_id=intent.operation_id,
        version_id=f"sha256-{'b' * 64}",
    )
    with pytest.raises(ValueError, match="cannot be reused"):
        ledger.register(changed)

    duplicate_id = f"event-{uuid4().hex}"
    duplicate_intent = make_intent(dataset_id=f"conformance.dataset.{uuid4().hex}")
    ledger.register(duplicate_intent)
    first = make_event(
        duplicate_intent,
        PublicationLifecycleEventType.VERSION_OBSERVED,
        event_id=duplicate_id,
    )
    ledger.append(first)
    conflicting = PublicationLifecycleEvent(
        event_id=duplicate_id,
        event_type=PublicationLifecycleEventType.HOLD_PLACED,
        dataset_id=first.dataset_id,
        occurred_at=_NOW,
        dataset_version=first.dataset_version,
    )
    with pytest.raises(ValueError, match="event ID"):
        ledger.append(conflicting)

    secret_event = PublicationLifecycleEvent(
        event_id=f"event-{uuid4().hex}",
        event_type=PublicationLifecycleEventType.VERSION_OBSERVED,
        dataset_id=f"conformance.dataset.{uuid4().hex}",
        occurred_at=_NOW,
        provider_operation_reference="postgresql://user:secret@db.example/test",
    )
    with pytest.raises(ValueError, match="credential or secret"):
        ledger.append(secret_event)
