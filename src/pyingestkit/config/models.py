from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LogOutputFormat(StrEnum):
    RICH = "rich"
    PLAIN = "plain"
    JSON = "json"


class FileLoggingConfig(BaseModel):
    """Optional rotating file logging configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    path: Path = Path(".pyingest/logs/pyingest.log")
    level: str = "DEBUG"
    format: LogOutputFormat = LogOutputFormat.JSON
    max_bytes: int = Field(default=10_000_000, ge=1)
    backup_count: int = Field(default=5, ge=0)

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.upper()
        if not isinstance(logging.getLevelName(normalized), int):
            raise ValueError(f"Unknown logging level: {value}")
        return normalized


class LoggingConfig(BaseModel):
    """Application logging policy used by the PyIngestKit CLI."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    level: str = "INFO"
    format: LogOutputFormat = LogOutputFormat.RICH
    console: bool = True
    file: FileLoggingConfig = Field(default_factory=FileLoggingConfig)

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.upper()
        if not isinstance(logging.getLevelName(normalized), int):
            raise ValueError(f"Unknown logging level: {value}")
        return normalized


class MetadataBackend(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class SQLiteMetadataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: Path | None = None


class PostgresMetadataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    dsn_env: str = "PYINGEST_DATABASE_URL"


class MetadataConfig(BaseModel):
    """Queryable runtime metadata backend configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    backend: MetadataBackend = MetadataBackend.SQLITE
    sqlite: SQLiteMetadataConfig = Field(default_factory=SQLiteMetadataConfig)
    postgres: PostgresMetadataConfig = Field(default_factory=PostgresMetadataConfig)


class PostgresTargetConfig(BaseModel):
    """Validated PostgreSQL target configuration without inline credentials."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    type: Literal["postgres"] = "postgres"
    target_id: str
    dsn_env: str = "PYINGEST_TARGET_DATABASE_URL"
    schema_name: str | None = Field(default="public", alias="schema")
    table: str
    load_mode: Literal["append", "truncate_load", "replace"] = "append"

    @field_validator("target_id", "dsn_env", "table")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("target_id")
    @classmethod
    def validate_target_id(cls, value: str) -> str:
        if "://" in value:
            raise ValueError("target_id must be a stable logical id, not a DSN")
        return value


class RuntimeConfig(BaseModel):
    """Validated runtime defaults loaded from project configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace: Path = Path(".pyingest")
    fixture_mode: bool = False
    parameters: dict[str, Any] = Field(default_factory=dict)


class PyIngestKitConfig(BaseModel):
    """Root configuration model for a PyIngestKit project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)
    targets: dict[str, PostgresTargetConfig] = Field(default_factory=dict)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
