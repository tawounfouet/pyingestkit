from __future__ import annotations

import pyingestkit
import pyingestkit.governance as governance

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


def test_lot23_governance_is_qualified_not_top_level() -> None:
    assert "PublicationLedger" in governance.__all__
    assert "ConditionalDatasetPublisher" in governance.__all__
    assert "DatasetVersionGarbageCollector" in governance.__all__
    assert "PublicationLedger" not in pyingestkit.__all__
    assert "RetentionPolicy" not in pyingestkit.__all__


def test_lot23_domain_and_ports_have_no_provider_imports() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files("domain/governance", "ports/governance.py", "governance")
    ).items():
        for module in modules:
            if matches_prefix(module, _PROVIDER_MODULES):
                violations.append(f"{path.name}: {module}")
    assert not violations, "\n".join(violations)


def test_lot23_adds_no_provider_adapter() -> None:
    assert python_files("adapters/governance") == ()
