"""PostgreSQL adapters for PyIngestKit V2."""

from pyingestkit.adapters.postgres.materializer import (
    PostgresDatasetMaterializer,
    PostgresDestination,
)

__all__ = ["PostgresDatasetMaterializer", "PostgresDestination"]
