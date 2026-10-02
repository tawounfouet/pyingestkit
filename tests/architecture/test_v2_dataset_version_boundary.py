from __future__ import annotations

from pyingestkit.datasets import DatasetVersion

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_IMPORTS = {
    "boto3",
    "duckdb",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
}


def test_dataset_version_domain_is_engine_and_store_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(python_files("domain/datasets/version.py")).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_dataset_version_surface_does_not_own_publication_or_storage() -> None:
    public = {name for name in dir(DatasetVersion) if not name.startswith("_")}

    assert {"dataset_id", "version_id", "row_count"}.issubset(public)
    assert public.isdisjoint({"publish", "rollback", "save", "store", "upload"})
