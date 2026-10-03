from __future__ import annotations

import pytest

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.domain.governance import PublicationLifecycleEventType

from tests.conformance.v2._governance_ledger_contract import (
    exercise_publication_ledger,
    make_event,
    make_intent,
)


def test_memory_publication_ledger_satisfies_shared_contract() -> None:
    exercise_publication_ledger(MemoryPublicationLedger())


def test_memory_transaction_rolls_back_operation_and_first_event_atomically() -> None:
    ledger = MemoryPublicationLedger()
    intent = make_intent()
    event = make_event(intent, PublicationLifecycleEventType.PUBLICATION_REQUESTED)

    with pytest.raises(RuntimeError, match="rollback"):
        with ledger.transaction() as transaction:
            transaction.register(intent)
            transaction.append(event)
            raise RuntimeError("rollback")

    assert ledger.get_operation(intent.operation_id) is None
    assert ledger.list_events(intent.operation_id) == ()


def test_memory_transaction_commits_operation_and_event_together() -> None:
    ledger = MemoryPublicationLedger()
    intent = make_intent()
    event = make_event(intent, PublicationLifecycleEventType.PUBLICATION_REQUESTED)

    with ledger.transaction() as transaction:
        transaction.register(intent)
        transaction.append(event)

    assert ledger.get_operation(intent.operation_id) == intent
    assert ledger.list_events(intent.operation_id) == (event,)
