from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_MATERIALIZATION_VALUES,
    V2_IMPLEMENTED_PUBLICATION_VALUES,
)
from pyingestkit.adapters.filesystem import FileCsvDatasetVersionMaterializerV2
from pyingestkit.datasets import ResourceDatasetVersionRequestV2
from pyingestkit.ports.dataset_materialization import DatasetVersionMaterializerV2
from pyingestkit.publication.v2 import (
    PublicationOutcomeUnknownError,
    PublicationReconciliationResultV2,
    PublicationReconciliationStatusV2,
    PublicationRequestV2,
    PublicationResultV2,
    PublicationServiceV2,
    PublicationStatusV2,
)

_EXPECTED_PUBLICATION = (
    "PublicationOutcomeUnknownError",
    "PublicationReconciliationResultV2",
    "PublicationReconciliationStatusV2",
    "PublicationRequestV2",
    "PublicationResultV2",
    "PublicationServiceV2",
    "PublicationStatusV2",
)

_EXPECTED_MATERIALIZATION = (
    "DatasetVersionMaterializerV2",
    "FileCsvDatasetVersionMaterializerV2",
    "ResourceDatasetVersionRequestV2",
)


def test_lot19_and_lot20_remain_recorded_as_completed() -> None:
    assert "LOT-19" in V2_COMPLETED_LOTS
    assert "LOT-20" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-20") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_lot20_publication_values_are_explicit() -> None:
    assert V2_IMPLEMENTED_PUBLICATION_VALUES == _EXPECTED_PUBLICATION
    assert PublicationServiceV2.__name__ == "PublicationServiceV2"
    assert PublicationRequestV2.__name__ == "PublicationRequestV2"
    assert PublicationResultV2.__name__ == "PublicationResultV2"
    assert PublicationStatusV2.UNKNOWN_OUTCOME.value == "unknown_outcome"
    assert PublicationReconciliationStatusV2.CONFIRMED_COMMITTED.value == "confirmed_committed"
    assert PublicationReconciliationResultV2.__name__ == ("PublicationReconciliationResultV2")
    assert issubclass(PublicationOutcomeUnknownError, RuntimeError)


def test_lot20_materialization_values_are_explicit() -> None:
    assert V2_IMPLEMENTED_MATERIALIZATION_VALUES == _EXPECTED_MATERIALIZATION
    assert isinstance(
        FileCsvDatasetVersionMaterializerV2(allowed_roots=(".",)),
        DatasetVersionMaterializerV2,
    )
    assert ResourceDatasetVersionRequestV2.__name__ == ("ResourceDatasetVersionRequestV2")
