"""Qualified V2 dataset materialization API during the V1 transition."""

from pyingestkit.adapters.postgres import (
    PostgresDatasetMaterializer,
    PostgresDestination,
)
from pyingestkit.domain.materialization import (
    MaterializationMode,
    MaterializationRequest,
    MaterializationResult,
    MaterializationStatus,
)
from pyingestkit.ports.materialization import DatasetMaterializer

__all__ = [
    "DatasetMaterializer",
    "MaterializationMode",
    "MaterializationRequest",
    "MaterializationResult",
    "MaterializationStatus",
    "PostgresDatasetMaterializer",
    "PostgresDestination",
]
