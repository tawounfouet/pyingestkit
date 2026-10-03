"""Versioned, non-executable PyIngestKit V2 serialization contracts."""

from pyingestkit.serialization.contracts_v2 import (
    SUPPORTED_BOUNDARY_CONTRACT_IDS,
    BoundaryContractCodecV2,
)
from pyingestkit.serialization.envelope_v2 import (
    ContractEnvelopeV2,
    ContractMigrationRegistryV2,
)

__all__ = [
    "BoundaryContractCodecV2",
    "ContractEnvelopeV2",
    "ContractMigrationRegistryV2",
    "SUPPORTED_BOUNDARY_CONTRACT_IDS",
]
