from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError

from pyingestkit.core.exceptions import ConfigurationError

from ._sqlalchemy import _SQLAlchemyMetadataStore


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return dsn


class PostgresMetadataStore(_SQLAlchemyMetadataStore):
    """PostgreSQL MetadataStore adapter backed by SQLAlchemy Core + psycopg."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ConfigurationError("PostgreSQL MetadataStore requires a non-empty DSN")
        self.dsn = dsn
        try:
            engine = self._create_engine(_normalize_dsn(dsn))
        except (ModuleNotFoundError, NoSuchModuleError) as exc:
            raise ConfigurationError(
                "PostgreSQL metadata backend requires psycopg. "
                "Install PyIngestKit with the 'postgres' extra."
            ) from exc
        try:
            super().__init__(engine)
        except ModuleNotFoundError as exc:
            raise ConfigurationError(
                "PostgreSQL metadata backend requires psycopg. "
                "Install PyIngestKit with the 'postgres' extra."
            ) from exc

    @staticmethod
    def _create_engine(dsn: str) -> Engine:
        return create_engine(dsn, future=True, pool_pre_ping=True)
