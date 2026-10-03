from __future__ import annotations

from pyingestkit._api_v2 import V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES
from pyingestkit.adapters.memory import MemoryPublicationLedger
from pyingestkit.ports.governance import PublicationLedger

from ._imports import imported_roots, matches_prefix, python_files

_PROVIDER_MODULES = {
    "boto3",
    "botocore",
    "httpx",
    "openpyxl",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "requests",
    "sqlalchemy",
}


def test_lot24_provider_inventory_is_explicit() -> None:
    assert V2_IMPLEMENTED_GOVERNANCE_PROVIDER_VALUES == (
        "MemoryPublicationLedger",
        "PostgresPublicationLedger",
    )


def test_memory_publication_ledger_is_base_package_safe() -> None:
    assert isinstance(MemoryPublicationLedger(), PublicationLedger)
    violations: list[str] = []
    for path, modules in imported_roots(python_files("adapters/memory")).items():
        for module in modules:
            if matches_prefix(module, _PROVIDER_MODULES):
                violations.append(f"{path.name}: {module}")
    assert not violations, "\n".join(violations)


def test_postgres_publication_ledger_does_not_reuse_historical_metadata_store() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files("adapters/postgres/publication_ledger.py")
    ).items():
        for module in modules:
            if matches_prefix(module, {"pyingestkit.metadata"}):
                violations.append(f"{path.name}: {module}")
    assert not violations, "\n".join(violations)
