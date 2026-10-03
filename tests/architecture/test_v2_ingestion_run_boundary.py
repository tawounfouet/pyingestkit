from __future__ import annotations

from pyingestkit.domain.runtime import IngestionResult, IngestionRun

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "boto3",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
    "pyingestkit.core",
    "pyingestkit.runtime.runner",
}


def test_lot09_execution_values_are_provider_and_legacy_runner_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("domain/runtime/execution.py")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_lot09_domain_values_do_not_execute_work() -> None:
    run_surface = {name for name in dir(IngestionRun) if not name.startswith("_")}
    result_surface = {name for name in dir(IngestionResult) if not name.startswith("_")}

    forbidden = {"acquire", "decode", "execute", "publish", "run", "validate"}
    assert run_surface.isdisjoint(forbidden)
    assert result_surface.isdisjoint(forbidden)
