"""Transactional PostgreSQL target adapter for PyIngestKit V2."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import MetaData, Table, create_engine, delete
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.exc import (
    ArgumentError,
    NoSuchModuleError,
    SQLAlchemyError,
)

from pyingestkit.adapters.postgres._schema import PostgresSchemaMapperV2
from pyingestkit.adapters.postgres._sql import (
    build_check_idempotence_sql,
    build_ensure_metadata_table_sql,
    build_merge_reconciliation_sql,
    build_record_target_load_sql,
    build_upsert_reconciliation_sql,
    create_temp_staging_table_sql,
)
from pyingestkit.domain.runtime import (
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)
from pyingestkit.domain.targets import (
    TargetLoadModeV2,
    TargetLoadRequestV2,
    TargetLoadResultV2,
    TargetLoadStatusV2,
)
from pyingestkit.ports.targets import TargetDescriptorV2

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_MAX_IDENTIFIER_BYTES = 63


class _PostgresConfigurationError(Exception):
    pass


class _PostgresProviderError(Exception):
    pass


class PostgresTargetV2:
    """Atomic PostgreSQL materialization for exact V2 DatasetVersion content."""

    _DESCRIPTOR = TargetDescriptorV2(
        id="pyingestkit.postgres",
        display_name="PostgreSQL",
        target_version="1",
        transactional=True,
        bulk_load=True,
        supported_modes=tuple(mode.value for mode in TargetLoadModeV2),
    )

    def __init__(
        self,
        *,
        target_id: str,
        dsn: str,
        default_schema: str | None = "public",
    ) -> None:
        if not isinstance(target_id, str) or not target_id.strip():
            raise ValueError("PostgresTargetV2 target_id must be non-blank.")
        if "://" in target_id:
            raise ValueError("PostgresTargetV2 target_id must be logical, not a DSN.")
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgresTargetV2 dsn must be non-blank.")
        if default_schema is not None:
            _validate_identifier(default_schema, label="schema")

        self._target_id = target_id.strip()
        self._raw_dsn = dsn
        self._normalized_dsn = _normalize_dsn(dsn)
        self._safe_dsn = _safe_dsn(dsn)
        self._default_schema = default_schema
        self._engine: Engine | None = None
        self._closed = False
        self._schema_mapper = PostgresSchemaMapperV2()

    @property
    def descriptor(self) -> TargetDescriptorV2:
        return self._DESCRIPTOR

    @property
    def target_id(self) -> str:
        return self._target_id

    @property
    def safe_dsn(self) -> str:
        return self._safe_dsn

    @property
    def closed(self) -> bool:
        return self._closed

    def load(self, request: TargetLoadRequestV2) -> TargetLoadResultV2:
        if not isinstance(request, TargetLoadRequestV2):
            raise TypeError("PostgresTargetV2.load expects TargetLoadRequestV2.")
        if self._closed:
            return self._failed(
                request,
                status=TargetLoadStatusV2.FAILED,
                code="target.postgres.closed",
                category=FailureCategory.CONFIGURATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="PostgreSQL target is closed.",
            )
        if request.target_id != self._target_id:
            return self._failed(
                request,
                status=TargetLoadStatusV2.FAILED,
                code="target.postgres.target_id_mismatch",
                category=FailureCategory.CONFIGURATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="Target load request does not match this PostgreSQL target.",
            )

        started_at = datetime.now(UTC)
        schema = self._default_schema if request.schema is None else request.schema
        destination = _destination(schema, request.table)

        # 1. Idempotency short-circuit
        if request.idempotent:
            try:
                engine = self._engine_for_load()
                if self._is_idempotent_duplicate(engine, schema, request, destination):
                    completed_at = datetime.now(UTC)
                    diagnostic = Diagnostic(
                        code="target.postgres.skipped_idempotent",
                        severity=DiagnosticSeverity.INFO,
                        summary="Target load skipped because exact dataset version was already materialized.",
                        stage="materialize",
                        target_context=self._target_id,
                        details=(
                            ("destination", destination),
                            ("mode", request.mode.value),
                            ("rows_loaded", str(len(request.representation))),
                            ("dataset_version_id", request.dataset_version.version_id),
                            ("reason", "idempotent_duplicate"),
                        ),
                        ingestion_run_id=request.ingestion_run_id,
                        correlation_id=request.correlation.correlation_id,
                    )
                    return TargetLoadResultV2(
                        load_id=str(uuid4()),
                        target_id=self._target_id,
                        ingestion_run_id=request.ingestion_run_id,
                        correlation=request.correlation,
                        dataset_version=request.dataset_version,
                        mode=request.mode,
                        status=TargetLoadStatusV2.SUCCEEDED,
                        destination=destination,
                        rows_input=len(request.representation),
                        rows_loaded=len(request.representation),
                        started_at=started_at,
                        completed_at=completed_at,
                        diagnostics=(diagnostic,),
                    )
            except _PostgresConfigurationError as exc:
                return self._failed(
                    request,
                    status=TargetLoadStatusV2.FAILED,
                    code="target.postgres.configuration",
                    category=FailureCategory.CONFIGURATION,
                    retryability=Retryability.NON_RETRYABLE,
                    summary=str(exc),
                    started_at=started_at,
                )

        # 2. Main transactional load execution
        load_id = str(uuid4())
        try:
            if schema is not None:
                _validate_identifier(schema, label="schema")
            _validate_identifier(request.table, label="table")
            for column in request.resolved_columns:
                _validate_identifier(column, label="column")
            for column in request.key_columns:
                _validate_identifier(column, label="key_column")
            for column in request.update_columns:
                _validate_identifier(column, label="update_column")

            plan = self._schema_mapper.plan(
                request.representation,
                request.resolved_columns,
            )
            engine = self._engine_for_load()
            with engine.begin() as connection:
                self._ensure_metadata_table(connection, schema)
                table = Table(
                    request.table,
                    MetaData(),
                    schema=schema,
                    autoload_with=connection,
                )
                self._schema_mapper.validate_table(plan, table)

                if request.mode in (TargetLoadModeV2.UPSERT, TargetLoadModeV2.MERGE):
                    rows_loaded = self._load_via_staging(connection, table, request)
                else:
                    self._prepare_mode(connection, table, request.mode)
                    rows_loaded = self._copy_to_table(connection, table.schema, table.name, request)

                completed_at = datetime.now(UTC)
                self._record_target_load(
                    connection,
                    schema=schema,
                    load_id=load_id,
                    destination=destination,
                    request=request,
                    rows_loaded=rows_loaded,
                    status="succeeded",
                    started_at=started_at,
                    completed_at=completed_at,
                )
        except _PostgresConfigurationError as exc:
            return self._failed(
                request,
                status=TargetLoadStatusV2.FAILED,
                code="target.postgres.configuration",
                category=FailureCategory.CONFIGURATION,
                retryability=Retryability.NON_RETRYABLE,
                summary=str(exc),
                started_at=started_at,
            )
        except ValueError as exc:
            return self._failed(
                request,
                status=TargetLoadStatusV2.FAILED,
                code="target.postgres.schema_mismatch",
                category=FailureCategory.CONFIGURATION,
                retryability=Retryability.NON_RETRYABLE,
                summary=str(exc),
                started_at=started_at,
            )
        except (_PostgresProviderError, SQLAlchemyError):
            return self._failed(
                request,
                status=TargetLoadStatusV2.ROLLED_BACK,
                code="target.postgres.load_rolled_back",
                category=FailureCategory.EXTERNAL_PROVIDER,
                retryability=Retryability.UNKNOWN,
                summary="PostgreSQL target load rolled back atomically.",
                started_at=started_at,
            )

        diagnostic = Diagnostic(
            code="target.postgres.succeeded",
            severity=DiagnosticSeverity.INFO,
            summary="PostgreSQL target materialization completed.",
            stage="materialize",
            target_context=self._target_id,
            details=(
                ("destination", destination),
                ("mode", request.mode.value),
                ("rows_loaded", str(rows_loaded)),
                ("dataset_version_id", request.dataset_version.version_id),
            ),
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return TargetLoadResultV2(
            load_id=load_id,
            target_id=self._target_id,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            dataset_version=request.dataset_version,
            mode=request.mode,
            status=TargetLoadStatusV2.SUCCEEDED,
            destination=destination,
            rows_input=len(request.representation),
            rows_loaded=rows_loaded,
            started_at=started_at,
            completed_at=completed_at,
            diagnostics=(diagnostic,),
        )

    def close(self) -> None:
        if self._closed:
            return
        if self._engine is not None:
            self._engine.dispose()
        self._closed = True

    def _engine_for_load(self) -> Engine:
        if self._engine is not None:
            return self._engine
        try:
            self._engine = create_engine(
                self._normalized_dsn,
                future=True,
                pool_pre_ping=True,
            )
        except (ModuleNotFoundError, NoSuchModuleError) as exc:
            raise _PostgresConfigurationError(
                "PostgresTargetV2 requires the 'postgres' extra."
            ) from exc
        except ArgumentError as exc:
            raise _PostgresConfigurationError("PostgresTargetV2 DSN is invalid.") from exc
        return self._engine

    @staticmethod
    def _prepare_mode(
        connection: Connection,
        table: Table,
        mode: TargetLoadModeV2,
    ) -> None:
        if mode is TargetLoadModeV2.APPEND:
            return
        if mode is TargetLoadModeV2.REPLACE:
            connection.execute(delete(table))
            return
        if mode is TargetLoadModeV2.TRUNCATE_LOAD:
            preparer = connection.dialect.identifier_preparer
            table_part = preparer.quote(table.name)
            qualified = (
                f"{preparer.quote(table.schema)}.{table_part}"
                if table.schema is not None
                else table_part
            )
            connection.exec_driver_sql(f"TRUNCATE TABLE {qualified}")
            return
        if mode in (TargetLoadModeV2.UPSERT, TargetLoadModeV2.MERGE):
            return
        raise _PostgresConfigurationError(f"Unsupported load mode: {mode.value}")

    def _copy_to_table(
        self,
        connection: Connection,
        table_schema: str | None,
        table_name: str,
        request: TargetLoadRequestV2,
    ) -> int:
        if not request.representation.records:
            return 0
        if connection.dialect.name != "postgresql":
            raise _PostgresConfigurationError("PostgresTargetV2 requires a PostgreSQL dialect.")

        try:
            from psycopg import Error as PsycopgError
        except ModuleNotFoundError as exc:
            raise _PostgresConfigurationError(
                "PostgresTargetV2 COPY requires the 'postgres' extra."
            ) from exc

        driver_connection: Any = connection.connection.driver_connection
        try:
            with driver_connection.cursor() as cursor:
                return self._execute_copy(cursor, table_schema, table_name, request)
        except (PsycopgError, TypeError, ValueError, OverflowError) as exc:
            raise _PostgresProviderError("PostgreSQL COPY failed.") from exc

    def _execute_copy(
        self,
        cursor: Any,
        target_schema: str | None,
        target_table: str,
        request: TargetLoadRequestV2,
    ) -> int:
        from psycopg import sql

        qualified = (
            sql.Identifier(target_schema, target_table)
            if target_schema is not None
            else sql.Identifier(target_table)
        )
        columns = sql.SQL(", ").join(sql.Identifier(column) for column in request.resolved_columns)
        statement = sql.SQL("COPY {} ({}) FROM STDIN").format(qualified, columns)

        rows_loaded = 0
        with cursor.copy(statement) as copy:
            for record in request.representation.records:
                values = tuple(_scalar_value(record, column) for column in request.resolved_columns)
                copy.write_row(values)
                rows_loaded += 1
        return rows_loaded

    def _load_via_staging(
        self,
        connection: Connection,
        table: Table,
        request: TargetLoadRequestV2,
    ) -> int:
        if not request.representation.records:
            return 0
        if connection.dialect.name != "postgresql":
            raise _PostgresConfigurationError("PostgresTargetV2 requires a PostgreSQL dialect.")

        try:
            from psycopg import Error as PsycopgError
        except ModuleNotFoundError as exc:
            raise _PostgresConfigurationError(
                "PostgresTargetV2 requires the 'postgres' extra."
            ) from exc

        driver_connection: Any = connection.connection.driver_connection
        staging_table = f"_stg_{uuid4().hex[:12]}"
        try:
            with driver_connection.cursor() as cursor:
                # 1. Create temporary staging table
                cursor.execute(
                    create_temp_staging_table_sql(staging_table, table.schema, table.name)
                )

                # 2. Bulk load data into staging table
                self._execute_copy(
                    cursor,
                    target_schema=None,
                    target_table=staging_table,
                    request=request,
                )

                # 3. SQL reconciliation from staging table into target table
                if request.mode is TargetLoadModeV2.UPSERT:
                    reconcile_sql = build_upsert_reconciliation_sql(
                        target_schema=table.schema,
                        target_table=table.name,
                        staging_table=staging_table,
                        columns=request.resolved_columns,
                        key_columns=request.key_columns,
                        update_columns=request.effective_update_columns,
                    )
                else:  # MERGE
                    server_ver = getattr(driver_connection.info, "server_version", 150000)
                    reconcile_sql = build_merge_reconciliation_sql(
                        target_schema=table.schema,
                        target_table=table.name,
                        staging_table=staging_table,
                        columns=request.resolved_columns,
                        key_columns=request.key_columns,
                        update_columns=request.effective_update_columns,
                        server_version_num=server_ver,
                    )
                cursor.execute(reconcile_sql)
        except (PsycopgError, TypeError, ValueError, OverflowError) as exc:
            raise _PostgresProviderError("PostgreSQL staging reconciliation failed.") from exc

        return len(request.representation.records)

    def _ensure_metadata_table(self, connection: Connection, schema: str | None) -> None:
        try:
            from psycopg import Error as PsycopgError
        except ModuleNotFoundError:
            return
        driver_connection: Any = connection.connection.driver_connection
        try:
            with driver_connection.cursor() as cursor:
                cursor.execute(build_ensure_metadata_table_sql(schema))
        except PsycopgError as exc:
            raise _PostgresProviderError("Failed to initialize target metadata table.") from exc

    def _is_idempotent_duplicate(
        self,
        engine: Engine,
        schema: str | None,
        request: TargetLoadRequestV2,
        destination: str,
    ) -> bool:
        try:
            from psycopg import Error as PsycopgError
        except ModuleNotFoundError:
            return False
        try:
            with engine.connect() as conn:
                driver_conn: Any = conn.connection.driver_connection
                with driver_conn.cursor() as cursor:
                    cursor.execute(
                        build_check_idempotence_sql(schema),
                        (
                            self._target_id,
                            destination,
                            request.dataset_version.version_id,
                            request.mode.value,
                        ),
                    )
                    return cursor.fetchone() is not None
        except (PsycopgError, SQLAlchemyError, OSError):
            return False

    def _record_target_load(
        self,
        connection: Connection,
        *,
        schema: str | None,
        load_id: str,
        destination: str,
        request: TargetLoadRequestV2,
        rows_loaded: int,
        status: str,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        try:
            from psycopg import Error as PsycopgError
        except ModuleNotFoundError:
            return
        driver_conn: Any = connection.connection.driver_connection
        try:
            with driver_conn.cursor() as cursor:
                cursor.execute(
                    build_record_target_load_sql(schema),
                    (
                        load_id,
                        self._target_id,
                        destination,
                        request.dataset_id,
                        request.dataset_version.version_id,
                        str(request.ingestion_run_id),
                        request.mode.value,
                        rows_loaded,
                        status,
                        started_at,
                        completed_at,
                    ),
                )
        except PsycopgError as exc:
            raise _PostgresProviderError("Failed to record target load metadata.") from exc

    def _failed(
        self,
        request: TargetLoadRequestV2,
        *,
        status: TargetLoadStatusV2,
        code: str,
        category: FailureCategory,
        retryability: Retryability,
        summary: str,
        started_at: datetime | None = None,
    ) -> TargetLoadResultV2:
        started = started_at or datetime.now(UTC)
        completed = datetime.now(UTC)
        schema = self._default_schema if request.schema is None else request.schema
        destination = _destination(schema, request.table)
        failure = FailureEvidence(
            error_code=code,
            category=category,
            retryability=retryability,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
            source_component="PostgresTargetV2",
            message_summary=summary,
            details=(
                ("destination", destination),
                ("dataset_version_id", request.dataset_version.version_id),
            ),
        )
        diagnostic = Diagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            summary=summary,
            stage="materialize",
            target_context=self._target_id,
            details=(
                ("destination", destination),
                ("mode", request.mode.value),
            ),
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return TargetLoadResultV2(
            load_id=str(uuid4()),
            target_id=self._target_id,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            dataset_version=request.dataset_version,
            mode=request.mode,
            status=status,
            destination=destination,
            rows_input=len(request.representation),
            rows_loaded=0,
            started_at=started,
            completed_at=completed,
            diagnostics=(diagnostic,),
            failure=failure,
        )


def _scalar_value(record: Any, column: str) -> None | bool | int | float | str:
    try:
        value = record.get(column)
    except KeyError:
        return None
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(f"PostgreSQL target cannot materialize nested field {column!r}.")


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
        return "<invalid-postgresql-dsn>"


def _validate_identifier(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise _PostgresConfigurationError(f"Unsafe PostgreSQL {label} identifier.")
    if len(value.encode("utf-8")) > _MAX_IDENTIFIER_BYTES:
        raise _PostgresConfigurationError(
            f"PostgreSQL {label} identifier exceeds {_MAX_IDENTIFIER_BYTES} bytes."
        )
    return value


def _destination(schema: str | None, table: str) -> str:
    return f"{schema + '.' if schema else ''}{table}"
