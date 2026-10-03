"""Metadata contracts with lazy provider loading.

The 2.0 base import must remain provider-neutral. PostgreSQL/SQLite factories are
resolved only when explicitly requested so migration/model imports do not pull
SQLAlchemy, psycopg or logging renderers into the base installation.
"""

from __future__ import annotations

from typing import Any

from .base import MetadataStore
from .capabilities import (
    DiffMetadataCapability,
    ReplayMetadataCapability,
    TargetLoadMetadataCapability,
    VersionMetadataCapability,
)
from .memory import MemoryMetadataStore
from .models import (
    ArtifactRecord,
    DatasetVersionRecord,
    DatasetVersionRunRecord,
    DiffRecord,
    EventRecord,
    PublicationRecord,
    PublishedDatasetRecord,
    ReplayRecord,
    ReproducibilityRecord,
    RunRecord,
    StepRecord,
    TargetLoadRecord,
    ValidationRecord,
)

__all__ = [
    "ArtifactRecord",
    "DatasetVersionRecord",
    "DatasetVersionRunRecord",
    "DiffMetadataCapability",
    "DiffRecord",
    "EventRecord",
    "MemoryMetadataStore",
    "MetadataStore",
    "PostgresMetadataStore",
    "PublicationRecord",
    "PublishedDatasetRecord",
    "ReplayMetadataCapability",
    "ReplayRecord",
    "ReproducibilityRecord",
    "RunRecord",
    "SQLiteMetadataStore",
    "StepRecord",
    "TargetLoadMetadataCapability",
    "TargetLoadRecord",
    "ValidationRecord",
    "VersionMetadataCapability",
    "create_metadata_store",
]


def __getattr__(name: str) -> Any:
    if name == "create_metadata_store":
        from .factory import create_metadata_store

        return create_metadata_store
    if name == "PostgresMetadataStore":
        from .postgres import PostgresMetadataStore

        return PostgresMetadataStore
    if name == "SQLiteMetadataStore":
        from .sqlite import SQLiteMetadataStore

        return SQLiteMetadataStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
