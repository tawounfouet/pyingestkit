from __future__ import annotations

import os
from pathlib import Path

from pyingestkit.config.models import MetadataBackend, MetadataConfig
from pyingestkit.core.exceptions import ConfigurationError

from .base import MetadataStore
from .postgres import PostgresMetadataStore
from .sqlite import SQLiteMetadataStore


def create_metadata_store(config: MetadataConfig, *, workspace: str | Path) -> MetadataStore:
    """Create the configured MetadataStore without leaking backend details into Runner."""
    if config.backend is MetadataBackend.SQLITE:
        path = config.sqlite.path or (Path(workspace) / "state" / "pyingest.sqlite3")
        return SQLiteMetadataStore(path)

    env_name = config.postgres.dsn_env
    dsn = os.getenv(env_name)
    if not dsn:
        raise ConfigurationError(
            f"PostgreSQL metadata backend expects DSN in environment variable {env_name!r}"
        )
    return PostgresMetadataStore(dsn)
