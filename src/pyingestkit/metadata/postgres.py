from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import ArgumentError, NoSuchModuleError, SQLAlchemyError

from pyingestkit.core.exceptions import ConfigurationError
from pyingestkit.logging.filters import redact_text

from ._sqlalchemy import _SQLAlchemyMetadataStore
from ._target_loads import SQLAlchemyTargetLoadMetadataMixin


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return dsn


def _safe_dsn(dsn: str) -> str:
    try:
        return make_url(_normalize_dsn(dsn)).render_as_string(hide_password=True)
    except ArgumentError:
        return redact_text(dsn)


class PostgresMetadataStore(SQLAlchemyTargetLoadMetadataMixin, _SQLAlchemyMetadataStore):
    """PostgreSQL MetadataStore adapter backed by SQLAlchemy Core + psycopg."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ConfigurationError("PostgreSQL MetadataStore requires a non-empty DSN")
        self._raw_dsn = dsn
        self._normalized_dsn = _normalize_dsn(dsn)
        self._safe_dsn = _safe_dsn(dsn)
        try:
            engine = self._create_engine(self._normalized_dsn)
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
        except SQLAlchemyError as exc:
            message = redact_text(str(exc))
            for secret_value in (self._raw_dsn, self._normalized_dsn):
                message = message.replace(secret_value, self.safe_dsn)
            raise ConfigurationError(
                f"Unable to initialize PostgreSQL metadata backend at {self.safe_dsn}: {message}"
            ) from exc

    @property
    def safe_dsn(self) -> str:
        """Credential-redacted DSN suitable for diagnostics."""

        return self._safe_dsn

    @staticmethod
    def _create_engine(dsn: str) -> Engine:
        return create_engine(dsn, future=True, pool_pre_ping=True)
