from __future__ import annotations

from pyingestkit.ports.dataset_versions import DatasetPublisher, DatasetVersionStore

from ._imports import imported_roots, matches_prefix, python_files

FORBIDDEN_CORE_IMPORTS = {
    "boto3",
    "pandas",
    "polars",
    "psycopg",
    "pyarrow",
    "pytransformkit",
    "pyworkflowkit",
    "sqlalchemy",
}


def test_lot08_ports_and_snapshot_codec_are_provider_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files(
            "ports/dataset_versions.py",
            "serialization/dataset_version_v2.py",
            "domain/datasets/publication.py",
        )
    ).items():
        for module in modules:
            if matches_prefix(module, FORBIDDEN_CORE_IMPORTS):
                violations.append(f"{path}: {module}")
    assert not violations, "\n".join(violations)


def test_version_store_and_publisher_are_separate_ports() -> None:
    store_surface = {name for name in dir(DatasetVersionStore) if not name.startswith("_")}
    publisher_surface = {name for name in dir(DatasetPublisher) if not name.startswith("_")}

    assert {"get", "list", "put", "read"}.issubset(store_surface)
    assert "publish" not in store_surface
    assert {"get_published", "publish"}.issubset(publisher_surface)
    assert "put" not in publisher_surface
