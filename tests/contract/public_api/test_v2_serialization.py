from __future__ import annotations

import pyingestkit.serialization as serialization
from pyingestkit._api_v2 import (
    V2_API_PHASE,
    V2_COMPLETED_LOTS,
    V2_IMPLEMENTED_SERIALIZATION_VALUES,
)
from pyingestkit.serialization import (
    SUPPORTED_BOUNDARY_CONTRACT_IDS,
    BoundaryContractCodecV2,
    ContractEnvelopeV2,
    ContractMigrationRegistryV2,
)

_EXPECTED = (
    "BoundaryContractCodecV2",
    "ContractEnvelopeV2",
    "ContractMigrationRegistryV2",
    "SUPPORTED_BOUNDARY_CONTRACT_IDS",
)


def test_lot16_phase_and_completed_lot_are_recorded() -> None:
    assert V2_API_PHASE == "LOT-16_CANONICAL_SERIALIZATION"
    assert V2_COMPLETED_LOTS[-1] == "LOT-16"


def test_lot16_serialization_values_are_explicit_and_importable() -> None:
    assert V2_IMPLEMENTED_SERIALIZATION_VALUES == _EXPECTED
    assert tuple(serialization.__all__) == _EXPECTED
    assert BoundaryContractCodecV2.__name__ == "BoundaryContractCodecV2"
    assert ContractEnvelopeV2.__name__ == "ContractEnvelopeV2"
    assert ContractMigrationRegistryV2.__name__ == "ContractMigrationRegistryV2"
    assert len(SUPPORTED_BOUNDARY_CONTRACT_IDS) == 10
