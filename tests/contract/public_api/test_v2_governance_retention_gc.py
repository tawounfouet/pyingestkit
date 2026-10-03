from __future__ import annotations

import pyingestkit.governance as governance
from pyingestkit.adapters.filesystem import FileDatasetVersionGarbageCollector
from pyingestkit.adapters.s3 import S3DatasetVersionGarbageCollector
from pyingestkit.governance.retention import (
    RetentionPlanner,
    RetentionState,
    RetentionStateLoader,
    VersionHoldRepository,
)
from pyingestkit.ports.governance import DatasetVersionGarbageCollector


def test_lot27_collectors_implement_frozen_gc_port() -> None:
    assert issubclass(FileDatasetVersionGarbageCollector, DatasetVersionGarbageCollector)
    assert issubclass(S3DatasetVersionGarbageCollector, DatasetVersionGarbageCollector)


def test_lot27_gc_providers_stay_in_explicit_provider_namespaces() -> None:
    assert FileDatasetVersionGarbageCollector.__module__ == (
        "pyingestkit.adapters.filesystem.garbage_collector"
    )
    assert S3DatasetVersionGarbageCollector.__module__ == (
        "pyingestkit.adapters.s3.garbage_collector"
    )


def test_lot27_retention_services_are_qualified_without_widening_frozen_governance_root() -> None:
    values = (
        RetentionPlanner,
        RetentionState,
        RetentionStateLoader,
        VersionHoldRepository,
    )
    assert all(value.__module__ == "pyingestkit.governance.retention" for value in values)
    assert "RetentionPlanner" not in governance.__all__
    assert "RetentionState" not in governance.__all__
