from __future__ import annotations

from pyingestkit.adapters.filesystem import FileDatasetVersionGarbageCollector
from pyingestkit.adapters.s3 import S3DatasetVersionGarbageCollector
from pyingestkit.governance.retention import RetentionPlanner
from pyingestkit.ports.governance import DatasetVersionGarbageCollector

from ._imports import imported_roots, matches_prefix, python_files

_PROVIDER_MODULES = {
    "boto3",
    "botocore",
    "psycopg",
    "sqlalchemy",
}


def test_lot27_retention_planner_stays_provider_neutral() -> None:
    violations: list[str] = []
    for path, modules in imported_roots(
        python_files("governance/retention.py", "governance/gc.py")
    ).items():
        for module in modules:
            if matches_prefix(module, _PROVIDER_MODULES):
                violations.append(f"{path.name}: {module}")
    assert not violations, "\n".join(violations)


def test_lot27_gc_capability_is_separate_from_dataset_version_store() -> None:
    assert issubclass(FileDatasetVersionGarbageCollector, DatasetVersionGarbageCollector)
    assert issubclass(S3DatasetVersionGarbageCollector, DatasetVersionGarbageCollector)
    assert RetentionPlanner.__module__ == "pyingestkit.governance.retention"
