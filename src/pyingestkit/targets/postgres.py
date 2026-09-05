from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any, Self
from uuid import uuid4

from sqlalchemy import MetaData, Table, create_engine, delete, insert
from sqlalchemy.engine import Connection, Engine, make_url
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
from .schema import PostgresSchemaMapper

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
    """PostgreSQL Dataset target using SQLAlchemy Core + psycopg COPY.

    V0.5.0-b2 supports APPEND, TRUNCATE_LOAD and REPLACE with one transaction
    per materialization. Idempotency decisions remain outside the Target and are
    implemented by TargetLoadExecutor over B1 target-load history.
    """

    A2_CAPABILITIES = TargetCapabilities(
        transactional=True,
        bulk_load=True,
        append=True,
        truncate_load=False,
        replace=False,
        upsert=False,
        staging=False,
        row_count_verification=False,
        schema_creation=False,
    )
    B2_CAPABILITIES = TargetCapabilities(
        transactional=True,
        bulk_load=True,
        append=True,
        truncate_load=True,
        replace=True,
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
        self._schema_mapper = PostgresSchemaMapper()
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
        return self.B2_CAPABILITIES

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

    def resolve_destination(self, request: TargetLoadRequest) -> str:
        schema = self.default_schema if request.schema is None else request.schema
        if schema is not None:
            _validate_identifier(schema, label="schema")
        _validate_identifier(request.table, label="table")
        return f"{schema + '.' if schema else ''}{request.table}"

    def load(self, request: TargetLoadRequest) -> TargetLoadResult:
        self._ensure_open()
        if request.target_id != self.target_id:
            raise TargetConfigurationError(
                "TargetLoadRequest targets "
                f"{request.target_id!r}, but this target is {self.target_id!r}"
            )
        if request.mode not in {
            LoadMode.APPEND,
            LoadMode.TRUNCATE_LOAD,
            LoadMode.REPLACE,
        }:
            raise UnsupportedLoadModeError(
                f"PostgresTarget V0.5.0-b2 does not support {request.mode.value!r}"
            )
        if (
            request.expected_row_count is not None
            and request.dataset.row_count != request.expected_row_count
        ):
            raise TargetConfigurationError(
                "TargetLoadRequest expected_row_count mismatch: "
                f"expected {request.expected_row_count}, got {request.dataset.row_count}"
            )

        schema = self.default_schema if request.schema is None else request.schema
        table_name = request.table
        if schema is not None:
            _validate_identifier(schema, label="schema")
        _validate_identifier(table_name, label="table")
        for field in request.dataset.fields:
            _validate_identifier(field, label="column")

        plan = self._schema_mapper.plan(request.dataset)
        started_at = datetime.now(UTC)
        started = time.perf_counter()
        rows_loaded = 0
        rows_cleared = 0
        try:
            with self._engine.begin() as connection:
                table = Table(table_name, MetaData(), schema=schema, autoload_with=connection)
                # Validate before destructive mutation so schema mismatches never clear data.
                self._schema_mapper.validate_table(plan, table)
                rows_cleared = self._prepare_table_for_mode(connection, table, request.mode)
                rows_loaded = self._load_rows(connection, table, request)
        except TargetConfigurationError:
            raise
        except (SQLAlchemyError, ValueError, TypeError) as exc:
            message = self._safe_error("PostgreSQL target load rolled back", exc)
            raise TargetLoadError(message) from exc

        completed_at = datetime.now(UTC)
        duration = max(time.perf_counter() - started, 0.0)
        destination = f"{schema + '.' if schema else ''}{table_name}"
        metrics: dict[str, int | float] = {
            "copy_rows": rows_loaded if self._engine.dialect.name == "postgresql" else 0,
            "rows_per_second": rows_loaded / duration if duration else 0.0,
            "content_reset": int(request.mode is not LoadMode.APPEND),
        }
        if request.mode is LoadMode.REPLACE:
            metrics["rows_deleted"] = rows_cleared
        return TargetLoadResult(
            load_id=str(uuid4()),
            target_id=self.target_id,
            dataset_id=request.dataset_id,
            dataset_version_id=request.dataset_version_id,
            run_id=request.run_id,
            mode=request.mode,
            status=TargetLoadStatus.SUCCESS,
            rows_input=request.dataset.row_count,
            rows_loaded=rows_loaded,
            rows_verified=None,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration,
            destination=destination,
            metrics=metrics,
        )

    def _prepare_table_for_mode(
        self,
        connection: Connection,
        table: Table,
        mode: LoadMode,
    ) -> int:
        if mode is LoadMode.APPEND:
            return 0
        if mode is LoadMode.TRUNCATE_LOAD:
            self._truncate_table(connection, table)
            return 0
        if mode is LoadMode.REPLACE:
            result = connection.execute(delete(table))
            return max(int(result.rowcount or 0), 0)
        raise UnsupportedLoadModeError(f"Unsupported load mode: {mode.value}")

    def _truncate_table(self, connection: Connection, table: Table) -> None:
        if connection.dialect.name != "postgresql":
            # Unit-test fallback. Production PostgreSQL uses transactional TRUNCATE.
            connection.execute(delete(table))
            return
        preparer = connection.dialect.identifier_preparer
        table_part = preparer.quote(table.name)
        qualified = (
            f"{preparer.quote(table.schema)}.{table_part}"
            if table.schema is not None
            else table_part
        )
        connection.exec_driver_sql(f"TRUNCATE TABLE {qualified}")

    def _load_rows(
        self,
        connection: Connection,
        table: Table,
        request: TargetLoadRequest,
    ) -> int:
        if request.dataset.row_count == 0:
            return 0
        if connection.dialect.name != "postgresql":
            connection.execute(insert(table), request.dataset.to_rows())
            return request.dataset.row_count
        return self._copy_rows(connection, request, schema=table.schema, table_name=table.name)

    def _copy_rows(
        self,
        connection: Connection,
        request: TargetLoadRequest,
        *,
        schema: str | None,
        table_name: str,
    ) -> int:
        try:
            from psycopg import Error as PsycopgError
            from psycopg import sql
        except ModuleNotFoundError as exc:
            raise TargetConfigurationError(
                "PostgresTarget COPY requires psycopg. "
                "Install PyIngestKit with the 'postgres' extra."
            ) from exc

        driver_connection: Any = connection.connection.driver_connection
        qualified = (
            sql.Identifier(schema, table_name) if schema is not None else sql.Identifier(table_name)
        )
        columns = sql.SQL(", ").join(sql.Identifier(field) for field in request.dataset.fields)
        statement = sql.SQL("COPY {} ({}) FROM STDIN").format(qualified, columns)

        rows_loaded = 0
        try:
            with driver_connection.cursor() as cursor:
                with cursor.copy(statement) as copy:
                    for row in request.dataset:
                        values = tuple(row.get(field) for field in request.dataset.fields)
                        copy.write_row(values)
                        rows_loaded += 1
        except (PsycopgError, TypeError, ValueError, OverflowError) as exc:
            message = self._safe_error("PostgreSQL COPY failed; transaction will roll back", exc)
            raise TargetLoadError(message) from exc
        return rows_loaded

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
