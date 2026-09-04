from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Self
from uuid import uuid4

from sqlalchemy import MetaData, Table, create_engine, insert
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import ArgumentError, NoSuchModuleError, SQLAlchemyError

from pyingestkit.logging.filters import redact_text

from .base import Target
from .capabilities import TargetCapabilities
from .errors import (
    InvalidTargetIdentifierError,
    TargetClosedError,
    TargetConfigurationError,
    TargetConnectionError,
    TargetLoadError,
    UnsupportedLoadModeError,
)
from .models import LoadMode, TargetLoadRequest, TargetLoadResult, TargetLoadStatus

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_MAX_IDENTIFIER_BYTES = 63


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


def _validate_identifier(value: str, *, label: str) -> str:
    if not value or not _IDENTIFIER.fullmatch(value):
        raise InvalidTargetIdentifierError(
            f"Unsafe PostgreSQL {label} identifier {value!r}; "
            "V0.5 requires standard unquoted identifiers"
        )
    if len(value.encode("utf-8")) > _MAX_IDENTIFIER_BYTES:
        raise InvalidTargetIdentifierError(
            f"PostgreSQL {label} identifier exceeds {_MAX_IDENTIFIER_BYTES} bytes"
        )
    return value


class PostgresTarget(Target):
    """PostgreSQL target foundation using SQLAlchemy Core and psycopg.

    V0.5.0-a1 provides safe connectivity, transaction lifecycle and a conservative
    parameterized APPEND path. PostgreSQL COPY and richer load semantics are added
    by later V0.5 milestones without changing the high-level Target contract.
    """

    A1_CAPABILITIES = TargetCapabilities(
        transactional=True,
        bulk_load=False,
        append=True,
        truncate_load=False,
        replace=False,
        upsert=False,
        staging=False,
        row_count_verification=False,
        schema_creation=False,
    )

    def __init__(
        self,
        *,
        target_id: str,
        dsn: str,
        default_schema: str | None = "public",
    ) -> None:
        if not target_id or not target_id.strip():
            raise TargetConfigurationError("PostgresTarget requires a non-empty target_id")
        if "://" in target_id:
            raise TargetConfigurationError("PostgresTarget.target_id must never be a DSN")
        if not dsn:
            raise TargetConfigurationError("PostgresTarget requires a non-empty DSN")
        if default_schema is not None:
            _validate_identifier(default_schema, label="schema")

        self._target_id = target_id.strip()
        self._raw_dsn = dsn
        self._normalized_dsn = _normalize_dsn(dsn)
        self._safe_dsn = _safe_dsn(dsn)
        self.default_schema = default_schema
        self._closed = False
        try:
            self._engine = self._create_engine(self._normalized_dsn)
        except (ModuleNotFoundError, NoSuchModuleError) as exc:
            raise TargetConfigurationError(
                "PostgresTarget requires psycopg. Install PyIngestKit with the 'postgres' extra."
            ) from exc

    @staticmethod
    def _create_engine(dsn: str) -> Engine:
        return create_engine(dsn, future=True, pool_pre_ping=True)

    @property
    def target_id(self) -> str:
        return self._target_id

    @property
    def capabilities(self) -> TargetCapabilities:
        return self.A1_CAPABILITIES

    @property
    def safe_dsn(self) -> str:
        """Credential-redacted DSN suitable for diagnostics."""

        return self._safe_dsn

    @property
    def closed(self) -> bool:
        return self._closed

    def open(self) -> Self:
        self._ensure_open()
        try:
            with self._engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
        except SQLAlchemyError as exc:
            message = self._safe_error("Unable to open PostgreSQL target", exc)
            raise TargetConnectionError(message) from exc
        return self

    def load(self, request: TargetLoadRequest) -> TargetLoadResult:
        self._ensure_open()
        if request.target_id != self.target_id:
            raise TargetConfigurationError(
                "TargetLoadRequest targets "
                f"{request.target_id!r}, but this target is {self.target_id!r}"
            )
        if request.mode is not LoadMode.APPEND:
            raise UnsupportedLoadModeError(
                f"PostgresTarget V0.5.0-a1 supports only {LoadMode.APPEND.value!r}; "
                f"requested {request.mode.value!r}"
            )

        schema = self.default_schema if request.schema is None else request.schema
        table_name = request.table
        if schema is not None:
            _validate_identifier(schema, label="schema")
        _validate_identifier(table_name, label="table")
        for field in request.dataset.fields:
            _validate_identifier(field, label="column")

        started_at = datetime.now(UTC)
        started = time.perf_counter()
        rows = request.dataset.to_rows()
        try:
            with self._engine.begin() as connection:
                table = Table(table_name, MetaData(), schema=schema, autoload_with=connection)
                table_columns = {column.name for column in table.columns}
                unknown = set(request.dataset.fields).difference(table_columns)
                if unknown:
                    names = ", ".join(sorted(unknown))
                    raise TargetConfigurationError(
                        f"Dataset fields are absent from PostgreSQL destination: {names}"
                    )
                if rows:
                    connection.execute(insert(table), rows)
        except TargetConfigurationError:
            raise
        except SQLAlchemyError as exc:
            message = self._safe_error("PostgreSQL target load rolled back", exc)
            raise TargetLoadError(message) from exc

        completed_at = datetime.now(UTC)
        duration = max(time.perf_counter() - started, 0.0)
        destination = f"{schema + '.' if schema else ''}{table_name}"
        return TargetLoadResult(
            load_id=str(uuid4()),
            target_id=self.target_id,
            dataset_id=request.dataset_id,
            dataset_version_id=request.dataset_version_id,
            run_id=request.run_id,
            mode=request.mode,
            status=TargetLoadStatus.SUCCESS,
            rows_input=request.dataset.row_count,
            rows_loaded=request.dataset.row_count,
            rows_verified=None,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            destination=destination,
            metrics={"rows_per_second": request.dataset.row_count / duration if duration else 0.0},
        )

    def close(self) -> None:
        if self._closed:
            return
        self._engine.dispose()
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise TargetClosedError(f"Target {self.target_id!r} has already been closed")

    def _safe_error(self, prefix: str, exc: BaseException) -> str:
        message = redact_text(str(exc))
        for secret_value in (self._raw_dsn, self._normalized_dsn):
            if secret_value:
                message = message.replace(secret_value, self.safe_dsn)
        return f"{prefix} for {self.target_id!r}: {message}"
