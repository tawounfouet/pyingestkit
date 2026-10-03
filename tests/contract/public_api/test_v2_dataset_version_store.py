from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_VERSION_STORE_VALUES,
)
from pyingestkit.datasets import PublishedDataset
from pyingestkit.publication.v2 import DatasetPublisher
from pyingestkit.stores import DatasetVersionStore, FileDatasetVersionStore


def test_lot08_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-08_VERSION_STORE_PUBLICATION"
    assert V2_COMPLETED_LOTS[-1] == "LOT-08"


def test_lot08_public_values_are_recorded() -> None:
    expected = {
        "DatasetPublisher",
        "DatasetVersionStore",
        "FileDatasetVersionStore",
        "PublishedDataset",
    }

    assert expected.issubset(V2_IMPLEMENTED_VERSION_STORE_VALUES)


def test_lot08_symbols_are_importable_from_v2_namespaces() -> None:
    assert PublishedDataset.__module__ == "pyingestkit.domain.datasets.publication"
    assert DatasetPublisher.__module__ == "pyingestkit.ports.dataset_versions"
    assert DatasetVersionStore.__module__ == "pyingestkit.ports.dataset_versions"
    assert FileDatasetVersionStore.__module__ == (
        "pyingestkit.adapters.filesystem.dataset_version_store"
    )
