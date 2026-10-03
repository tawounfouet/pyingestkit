from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_PYTRANSFORMKIT_VALUES,
)
from pyingestkit.integrations import pytransformkit

_EXPECTED = (
    "DatasetVersionInputAdapter",
    "PyTransformKitCompatibilityError",
    "PyTransformKitIntegrationError",
    "PyTransformKitMappingError",
    "PyTransformKitUnavailableError",
    "TransformationPublicationAdapter",
    "TransformationPublicationInput",
    "from_transform_correlation",
    "from_transform_failure",
    "pytransformkit_version",
    "to_transform_correlation",
)


def test_lot17_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-17_PYTRANSFORMKIT_INTEGRATION"
    assert V2_COMPLETED_LOTS[-1] == "LOT-17"


def test_lot17_optional_integration_values_are_explicit() -> None:
    assert V2_IMPLEMENTED_PYTRANSFORMKIT_VALUES == _EXPECTED
    assert tuple(pytransformkit.__all__) == _EXPECTED


def test_lot17_integration_imports_without_loading_sibling() -> None:
    assert pytransformkit.DatasetVersionInputAdapter.__module__ == (
        "pyingestkit.integrations.pytransformkit.adapters"
    )
