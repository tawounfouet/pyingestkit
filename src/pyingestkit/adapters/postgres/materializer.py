"""PostgreSQL DatasetVersion materializer for PyIngestKit V2."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

from sqlalchemy import (
    Boolean,
    Float,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    create_engine,
    delete,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import NoSuchModuleError, SQLAlchemyError
from sqlalchemy.sql.sqltypes import NullType

from pyingestkit.domain.decoding import (
    DecodedArray,
    DecodedObject,
    DecodedType,
)
from pyingestkit.domain.materialization import (
    MaterializationMode,
    MaterializationRequest,
    MaterializationResult,
    MaterializationStatus,
)
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import (
    Diagnostic,
    DiagnosticSeverity,
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")
_MAX_IDENTIFIER_BYTES = 63
_POSTGRES_DESTINATION_NAMESPACE = "pyingestkit.destination.postgres"


@dataclass(frozen=True, slots=True)
class PostgresDestination:
    """Credential-free PostgreSQL table destination."""

    table: str
    schema: str = "public"

    def __post_init__(self) -> None:
        _validate_identifier(self.schema, label="schema")
        _validate_identifier(self.table, label="table")

    @property
    def resource(self) -> ResourceReference:
        return ResourceReference(
            namespace=_POSTGRES_DESTINATION_NAMESPACE,
            resource_id=f"{self.schema}.{self.table}",
            locator=f"postgresql-table:///{self.schema}/{self.table}",
            format="postgresql-table",
            metadata=(("schema", self.schema), ("table", self.table)),
        )

    @classmethod
    def from_resource(cls, resource: ResourceReference) -> PostgresDestination:
        if not isinstance(resource, ResourceReference):
            raise TypeError("PostgresDestination resource must be ResourceReference.")
        if resource.namespace != _POSTGRES_DESTINATION_NAMESPACE:
            raise ValueError("PostgreSQL materialization requires a PostgreSQL destination.")
        metadata = dict(resource.metadata)
        schema = metadata.get("schema")
        table = metadata.get("table")
        if schema is None or table is None:
            raise ValueError("PostgreSQL destination must record schema and table metadata.")
        destination = cls(schema=schema, table=table)
        if resource.resource_id != f"{destination.schema}.{destination.table}":
            raise ValueError("PostgreSQL destination resource identity is inconsistent.")
        if resource.locator != destination.resource.locator:
            raise ValueError("PostgreSQL destination locator is inconsistent.")
        return destination


class PostgresDatasetMaterializer:
    """Materialize immutable V2 DatasetVersion values into an existing PostgreSQL table."""

    def __init__(
        self,
        *,
        dsn: str,
        materializer_id: str = "pyingestkit.postgres",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(dsn, str) or not dsn.strip():
            raise ValueError("PostgresDatasetMaterializer requires a non-blank DSN.")
        if not isinstance(materializer_id, str) or not materializer_id.strip():
            raise ValueError(
                "PostgresDatasetMaterializer materializer_id must be non-blank text."
            )
        self._dsn = _normalize_dsn(dsn.strip())
        self._materializer_id = materializer_id.strip()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._engine: Engine | None = None

    @property
    def materializer_id(self) -> str:
        return self._materializer_id

    @property
    def closed(self) -> bool:
        return self._engine is None

    def open(self) -> Self:
        engine = self._ensure_engine()
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
        except SQLAlchemyError as exc:
            raise RuntimeError("PostgreSQL materializer connection check failed.") from exc
        return self

    def materialize(self, request: MaterializationRequest) -> MaterializationResult:
        if not isinstance(request, MaterializationRequest):
            raise TypeError(
                "PostgresDatasetMaterializer.materialize requires MaterializationRequest."
            )
        started_at = self._now()

        try:
            destination = PostgresDestination.from_resource(request.destination)
            fields = self._preflight_dataset(request)
            engine = self._ensure_engine()
        except (TypeError, ValueError, ModuleNotFoundError, NoSuchModuleError) as exc:
            return self._failed(
                request,
                started_at=started_at,
                code="materialization.postgres.configuration",
                category=FailureCategory.CONFIGURATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="PostgreSQL materialization configuration is invalid.",
                details=(("exception_type", type(exc).__name__),),
            )

        rows_cleared = 0
        try:
            with engine.begin() as connection:
                table = Table(
                    destination.table,
                    MetaData(),
                    schema=destination.schema,
                    autoload_with=connection,
                )
                self._validate_table(request, table, fields)
                rows_cleared = self._prepare_table(connection, table, request.mode)
                rows_loaded = self._copy_rows(
                    connection,
                    table,
                    request,
                    fields=fields,
                )
        except SQLAlchemyError as exc:
            return self._failed(
                request,
                started_at=started_at,
                code="materialization.postgres.database",
                category=FailureCategory.SIDE_EFFECT_FAILED,
                retryability=Retryability.UNKNOWN,
                summary="PostgreSQL materialization rolled back.",
                details=(("exception_type", type(exc).__name__),),
            )
        except (TypeError, ValueError, OverflowError) as exc:
            return self._failed(
                request,
                started_at=started_at,
                code="materialization.postgres.contract",
                category=FailureCategory.CONTRACT_VIOLATION,
                retryability=Retryability.NON_RETRYABLE,
                summary="DatasetVersion cannot satisfy the PostgreSQL destination contract.",
                details=(("exception_type", type(exc).__name__),),
            )

        completed_at = self._now()
        diagnostic = Diagnostic(
            code="materialization.postgres.succeeded",
            severity=DiagnosticSeverity.INFO,
            summary="DatasetVersion materialized in PostgreSQL.",
            stage="materialize",
            source_context=self.materializer_id,
            details=(
                ("destination", request.destination.resource_id),
                ("mode", request.mode.value),
                ("rows_loaded", str(rows_loaded)),
                ("rows_cleared", str(rows_cleared)),
            ),
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return MaterializationResult(
            status=MaterializationStatus.SUCCEEDED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            dataset_version=request.dataset_version.reference,
            destination=request.destination,
            mode=request.mode,
            rows_input=request.dataset_version.row_count,
            rows_loaded=rows_loaded,
            rows_cleared=rows_cleared,
            started_at=started_at,
            completed_at=completed_at,
            diagnostics=(diagnostic,),
        )

    def close(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def _ensure_engine(self) -> Engine:
        if self._engine is not None:
            return self._engine
        try:
            self._engine = create_engine(self._dsn, future=True, pool_pre_ping=True)
        except (ModuleNotFoundError, NoSuchModuleError) as exc:
            raise ModuleNotFoundError(
                "PostgreSQL materialization requires the 'postgres' extra."
            ) from exc
        return self._engine

    @staticmethod
    def _preflight_dataset(request: MaterializationRequest) -> tuple[str, ...]:
        fields = tuple(field.name for field in request.dataset_version.schema.fields)
        for field in fields:
            _validate_identifier(field, label="column")
        if len(set(fields)) != len(fields):
            raise ValueError("DatasetVersion schema contains duplicate field names.")

        for record in request.dataset_version.representation.records:
            record_fields = tuple(name for name, _ in record.fields)
            if record_fields != fields:
                raise ValueError(
                    "DatasetVersion record fields/order must match schema evidence exactly."
                )
            for _, value in record.fields:
                if isinstance(value, DecodedObject | DecodedArray):
                    raise TypeError(
                        "PostgreSQL LOT-14 accepts scalar decoded values only; "
                        "object/array mapping requires an explicit future policy."
                    )
        return fields

    @staticmethod
    def _validate_table(
        request: MaterializationRequest,
        table: Table,
        fields: tuple[str, ...],
    ) -> None:
        columns = {column.name: column for column in table.columns}
        missing = [field for field in fields if field not in columns]
        if missing:
            raise ValueError(
                "DatasetVersion fields are absent from PostgreSQL destination: "
                + ", ".join(missing)
            )

        evidence_by_name = {
            field.name: field for field in request.dataset_version.schema.fields
        }
        mismatches: list[str] = []
        for name in fields:
            evidence = evidence_by_name[name]
            column = columns[name]
            if evidence.nullable and not column.nullable:
                mismatches.append(f"{name}: nullable source -> NOT NULL destination")
                continue
            observed = tuple(
                item for item in evidence.observed_types if item is not DecodedType.NULL
            )
            if not observed:
                continue
            if any(item in {DecodedType.OBJECT, DecodedType.ARRAY} for item in observed):
                mismatches.append(f"{name}: nested decoded values are unsupported")
                continue
            if not all(_is_type_compatible(item, column.type) for item in observed):
                kinds = ",".join(item.value for item in observed)
                mismatches.append(
                    f"{name}: decoded={kinds}, destination={column.type}"
                )
        if mismatches:
            raise ValueError(
                "PostgreSQL destination schema mismatch: " + "; ".join(mismatches)
            )

    @staticmethod
    def _prepare_table(
        connection: Connection,
        table: Table,
        mode: MaterializationMode,
    ) -> int:
        if mode is MaterializationMode.APPEND:
            return 0
        if mode is MaterializationMode.TRUNCATE_LOAD:
            preparer = connection.dialect.identifier_preparer
            table_part = preparer.quote(table.name)
            qualified = (
                f"{preparer.quote(table.schema)}.{table_part}"
                if table.schema is not None
                else table_part
            )
            connection.exec_driver_sql(f"TRUNCATE TABLE {qualified}")
            return 0
        if mode is MaterializationMode.REPLACE:
            result = connection.execute(delete(table))
            return max(int(result.rowcount or 0), 0)
        raise ValueError(f"Unsupported materialization mode: {mode!r}.")

    @staticmethod
    def _copy_rows(
        connection: Connection,
        table: Table,
        request: MaterializationRequest,
        *,
        fields: tuple[str, ...],
    ) -> int:
        if request.dataset_version.row_count == 0:
            return 0
        try:
            from psycopg import Error as PsycopgError
            from psycopg import sql
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "PostgreSQL COPY requires the 'postgres' extra."
            ) from exc

        driver_connection: Any = connection.connection.driver_connection
        qualified = (
            sql.Identifier(table.schema, table.name)
            if table.schema is not None
            else sql.Identifier(table.name)
        )
        columns = sql.SQL(", ").join(sql.Identifier(field) for field in fields)
        statement = sql.SQL("COPY {} ({}) FROM STDIN").format(qualified, columns)

        rows_loaded = 0
        try:
            with driver_connection.cursor() as cursor:
                with cursor.copy(statement) as copy:
                    for record in request.dataset_version.representation.records:
                        values_by_name = dict(record.fields)
                        copy.write_row(tuple(values_by_name[field] for field in fields))
                        rows_loaded += 1
        except PsycopgError as exc:
            raise SQLAlchemyError("PostgreSQL COPY failed.") from exc
        return rows_loaded

    def _failed(
        self,
        request: MaterializationRequest,
        *,
        started_at: datetime,
        code: str,
        category: FailureCategory,
        retryability: Retryability,
        summary: str,
        details: tuple[tuple[str, str], ...] = (),
    ) -> MaterializationResult:
        completed_at = self._now()
        failure = FailureEvidence(
            error_code=code,
            category=category,
            retryability=retryability,
            uncertainty=OutcomeUncertainty.KNOWN,
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
            source_component=self.materializer_id,
            message_summary=summary,
            details=details,
        )
        diagnostic = Diagnostic(
            code=code,
            severity=DiagnosticSeverity.ERROR,
            summary=summary,
            stage="materialize",
            source_context=self.materializer_id,
            details=details,
            ingestion_run_id=request.ingestion_run_id,
            correlation_id=request.correlation.correlation_id,
        )
        return MaterializationResult(
            status=MaterializationStatus.FAILED,
            ingestion_run_id=request.ingestion_run_id,
            correlation=request.correlation,
            dataset_version=request.dataset_version.reference,
            destination=request.destination,
            mode=request.mode,
            rows_input=request.dataset_version.row_count,
            rows_loaded=0,
            rows_cleared=0,
            started_at=started_at,
            completed_at=completed_at,
            diagnostics=(diagnostic,),
            failure=failure,
        )

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ValueError(
                "PostgresDatasetMaterializer clock must return timezone-aware datetime."
            )
        return value


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("postgres://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgres://")
    if dsn.startswith("postgresql://"):
        return "postgresql+psycopg://" + dsn.removeprefix("postgresql://")
    return dsn


def _validate_identifier(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or not _IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"Unsafe PostgreSQL {label} identifier {value!r}; "
            "LOT-14 requires standard unquoted identifiers."
        )
    if len(value.encode("utf-8")) > _MAX_IDENTIFIER_BYTES:
        raise ValueError(
            f"PostgreSQL {label} identifier exceeds {_MAX_IDENTIFIER_BYTES} bytes."
        )
    return value


def _is_type_compatible(decoded_type: DecodedType, sql_type: object) -> bool:
    if isinstance(sql_type, NullType):
        return False
    if decoded_type is DecodedType.STRING:
        return isinstance(sql_type, String)
    if decoded_type is DecodedType.INTEGER:
        return isinstance(sql_type, Integer)
    if decoded_type is DecodedType.NUMBER:
        return isinstance(sql_type, Float | Numeric)
    if decoded_type is DecodedType.BOOLEAN:
        return isinstance(sql_type, Boolean)
    return decoded_type is DecodedType.NULL
