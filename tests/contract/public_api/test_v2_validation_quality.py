from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_VALIDATION_VALUES,
)
from pyingestkit.quality.v2 import QualityEvidence
from pyingestkit.validation.v2 import (
    MinimumRowsV2,
    RequiredFieldV2,
    UniqueFieldV2,
    ValidationLimits,
    ValidationRequest,
    ValidationRuleV2,
    validate_v2,
)


def test_lot06_phase_and_completed_lot_are_recorded() -> None:
    assert "LOT-06" in V2_COMPLETED_LOTS
    assert V2_COMPLETED_LOTS.index("LOT-06") <= V2_COMPLETED_LOTS.index(V2_COMPLETED_LOTS[-1])
    assert V2_API_PHASE.startswith("LOT-")


def test_lot06_public_values_are_recorded() -> None:
    expected = {
        "MinimumRowsV2",
        "QualityEvidence",
        "RequiredFieldV2",
        "UniqueFieldV2",
        "ValidationLimits",
        "ValidationRequest",
        "ValidationRuleV2",
        "validate_v2",
    }

    assert expected.issubset(V2_IMPLEMENTED_VALIDATION_VALUES)


def test_lot06_symbols_are_importable_from_owned_namespaces() -> None:
    assert QualityEvidence.__module__ == "pyingestkit.quality.v2"
    assert ValidationRequest.__module__ == "pyingestkit.validation.v2"
    assert ValidationLimits.__module__ == "pyingestkit.validation.v2"
    assert ValidationRuleV2.__module__ == "pyingestkit.validation.v2"
    assert MinimumRowsV2.__module__ == "pyingestkit.validation.v2"
    assert RequiredFieldV2.__module__ == "pyingestkit.validation.v2"
    assert UniqueFieldV2.__module__ == "pyingestkit.validation.v2"
    assert validate_v2.__module__ == "pyingestkit.validation.v2"
