from __future__ import annotations

from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.adapters.postgres import PostgresPublicationLedger
from pyingestkit.ports.governance import PublicationLedger


def test_lot24_adapters_implement_frozen_publication_ledger_port() -> None:
    assert issubclass(MemoryPublicationLedger, PublicationLedger)
    assert issubclass(PostgresPublicationLedger, PublicationLedger)


def test_lot24_adapters_live_in_explicit_provider_namespaces() -> None:
    assert MemoryPublicationLedger.__module__ == ("pyingestkit.adapters.memory.publication_ledger")
    assert PostgresPublicationLedger.__module__ == (
        "pyingestkit.adapters.postgres.publication_ledger"
    )
