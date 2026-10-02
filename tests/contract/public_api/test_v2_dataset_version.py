from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_DATASET_VERSION_VALUES,
)
from pyingestkit.datasets import (
    DatasetVersion,
    DatasetVersionReference,
    build_dataset_version,
    dataset_content_fingerprint,
)


def test_lot07_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-07_DATASET_VERSION"
    assert V2_COMPLETED_LOTS[-1] == "LOT-07"


def test_lot07_public_values_are_recorded() -> None:
    expected = {
        "DatasetVersion",
        "DatasetVersionReference",
        "build_dataset_version",
        "dataset_content_fingerprint",
    }

    assert expected.issubset(V2_IMPLEMENTED_DATASET_VERSION_VALUES)


def test_lot07_symbols_are_importable_from_v2_dataset_namespace() -> None:
    assert DatasetVersion.__module__ == "pyingestkit.domain.datasets.version"
    assert DatasetVersionReference.__module__ == "pyingestkit.domain.datasets.references"
    assert build_dataset_version.__module__ == "pyingestkit.domain.datasets.version"
    assert dataset_content_fingerprint.__module__ == "pyingestkit.domain.datasets.version"
