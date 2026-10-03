from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import inspect

from pyingestkit.adapters.postgres import PostgresPublicationLedger
from pyingestkit.domain.governance import PublicationLifecycleEventType, VersionHold
from tests.conformance.v2._governance_ledger_contract import (
    exercise_publication_ledger,
    make_event,
    make_intent,
)

POSTGRES_DSN = os.getenv("PYINGEST_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not POSTGRES_DSN,
    reason="PYINGEST_TEST_POSTGRES_DSN is required for lifecycle-ledger E2E",
)


def test_postgres_publication_ledger_satisfies_shared_contract() -> None:
    assert POSTGRES_DSN is not None
    ledger = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        exercise_publication_ledger(ledger)
    finally:
        ledger.close()


def test_postgres_transaction_commit_and_rollback_are_atomic() -> None:
    assert POSTGRES_DSN is not None
    ledger = PostgresPublicationLedger(POSTGRES_DSN)
    rollback_intent = make_intent()
    rollback_event = make_event(
        rollback_intent,
        PublicationLifecycleEventType.PUBLICATION_REQUESTED,
    )
    committed_intent = make_intent()
    committed_event = make_event(
        committed_intent,
        PublicationLifecycleEventType.PUBLICATION_REQUESTED,
    )

    try:
        with pytest.raises(RuntimeError, match="force rollback"):
            with ledger.transaction() as transaction:
                transaction.register(rollback_intent)
                transaction.append(rollback_event)
                raise RuntimeError("force rollback")

        assert ledger.get_operation(rollback_intent.operation_id) is None
        assert ledger.list_events(rollback_intent.operation_id) == ()

        with ledger.transaction() as transaction:
            transaction.register(committed_intent)
            transaction.append(committed_event)

        assert ledger.get_operation(committed_intent.operation_id) == committed_intent
        assert ledger.list_events(committed_intent.operation_id) == (committed_event,)
    finally:
        ledger.close()


def test_postgres_restart_recovers_unresolved_operation_and_exact_event_history() -> None:
    assert POSTGRES_DSN is not None
    dataset_id = f"restart.dataset.{uuid4().hex}"
    intent = make_intent(dataset_id=dataset_id)
    requested = make_event(
        intent,
        PublicationLifecycleEventType.PUBLICATION_REQUESTED,
    )

    first = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        with first.transaction() as transaction:
            transaction.register(intent)
            transaction.append(requested)
    finally:
        first.close()

    restarted = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        assert restarted.get_operation(intent.operation_id) == intent
        assert restarted.list_unresolved(dataset_id) == (intent,)
        assert restarted.list_events(intent.operation_id) == (requested,)

        committed = make_event(
            intent,
            PublicationLifecycleEventType.PUBLICATION_COMMITTED,
        )
        restarted.append(committed)

        assert restarted.list_unresolved(dataset_id) == ()
        assert restarted.list_events(intent.operation_id) == (requested, committed)
    finally:
        restarted.close()


def test_postgres_concurrent_append_has_stable_observable_order() -> None:
    assert POSTGRES_DSN is not None
    ledger = PostgresPublicationLedger(POSTGRES_DSN)
    intent = make_intent()
    first = make_event(intent, PublicationLifecycleEventType.VERSION_OBSERVED)
    second = make_event(intent, PublicationLifecycleEventType.VERSION_OBSERVED)

    try:
        ledger.register(intent)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(ledger.append, first),
                executor.submit(ledger.append, second),
            ]
            for future in futures:
                future.result()

        observed_once = ledger.list_events(intent.operation_id)
        observed_twice = ledger.list_events(intent.operation_id)

        assert observed_once == observed_twice
        assert {event.event_id for event in observed_once} == {
            first.event_id,
            second.event_id,
        }
    finally:
        ledger.close()


def test_postgres_lifecycle_schema_is_additive_and_dsn_is_redacted() -> None:
    assert POSTGRES_DSN is not None
    ledger = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        tables = set(inspect(ledger.engine).get_table_names())
        assert {
            "pyingestkit_v2_publication_operation",
            "pyingestkit_v2_publication_event",
            "pyingestkit_v2_version_hold",
        }.issubset(tables)
        assert "postgres:postgres@" not in ledger.safe_dsn
    finally:
        ledger.close()



def test_postgres_version_hold_survives_restart_and_releases_durably() -> None:
    assert POSTGRES_DSN is not None
    dataset_id = f"hold.dataset.{uuid4().hex}"
    reference = make_intent(dataset_id=dataset_id).dataset_version
    held_at = datetime(2026, 10, 4, 2, 30, tzinfo=UTC)
    hold = VersionHold(reference, held_at=held_at, reason="legal-review")

    first = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        assert first.place_hold(hold) == hold
        active = first.list_active_holds(dataset_id)
        assert len(active) == 1
        assert active[0].dataset_version.identity == reference.identity
        assert active[0].held_at == held_at
        assert active[0].reason == "legal-review"
    finally:
        first.close()

    restarted = PostgresPublicationLedger(POSTGRES_DSN)
    try:
        active = restarted.list_active_holds(dataset_id)
        assert len(active) == 1
        assert active[0].dataset_version.identity == reference.identity

        released_at = held_at + timedelta(minutes=5)
        assert restarted.release_hold(reference, released_at=released_at) is True
        assert restarted.release_hold(reference, released_at=released_at) is False
        assert restarted.list_active_holds(dataset_id) == ()

        events = restarted.list_events(dataset_id=dataset_id)
        assert [event.event_type for event in events] == [
            PublicationLifecycleEventType.HOLD_PLACED,
            PublicationLifecycleEventType.HOLD_RELEASED,
        ]
    finally:
        restarted.close()
