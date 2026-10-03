from __future__ import annotations

import pyingestkit.targets as v1_targets
from pyingestkit.adapters.postgres import PostgresTargetV2
from pyingestkit.ports.targets import DatasetTargetV2

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_CORE_IMPORTS = {
    "psycopg",
    "sqlalchemy",
    "pyingestkit.targets",
    "pyingestkit.dataset",
    "pyingestkit.core",
}


def test_lot14_target_domain_and_port_are_provider_and_v1_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("domain/targets", "ports/targets.py")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_CORE_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot14_postgres_adapter_does_not_import_v1_target_contracts() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("adapters/postgres")).items():
        for module in modules:
            if module == "pyingestkit.targets" or module.startswith("pyingestkit.targets."):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot14_target_is_port_compatible_without_v1_inheritance() -> None:
    assert DatasetTargetV2.__module__ == "pyingestkit.ports.targets"
    assert PostgresTargetV2.__module__ == "pyingestkit.adapters.postgres.target"
    assert not issubclass(PostgresTargetV2, v1_targets.Target)


def test_v1_target_namespace_remains_exact_during_lot14() -> None:
    assert v1_targets.__all__ == [
        "IdempotencyAction",
        "IdempotencyPolicy",
        "InvalidTargetIdentifierError",
        "LoadMode",
        "PostgresTarget",
        "Target",
        "TargetCapabilities",
        "TargetClosedError",
        "TargetConfigurationError",
        "TargetConnectionError",
        "TargetError",
        "TargetLoadConflictError",
        "TargetLoadDecision",
        "TargetLoadError",
        "TargetLoadExecutor",
        "TargetLoadRequest",
        "TargetLoadResult",
        "TargetLoadStatus",
        "UnsupportedLoadModeError",
    ]
