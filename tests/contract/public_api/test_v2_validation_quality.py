from __future__ import annotations

from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_VALIDATION_VALUES,
)
from pyingestkit.quality import QualityEvidence
from pyingestkit.validation import (
    MinimumRowsV2,
    RequiredFieldV2,
    UniqueFieldV2,
    ValidationLimits,
    ValidationRequest,
    ValidationRuleV2,
    validate_v2,
)


def test_lot06_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-06_VALIDATION_QUALITY"
    assert V2_COMPLETED_LOTS[-1] == "LOT-06"


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
