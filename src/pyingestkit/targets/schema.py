from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, Integer, LargeBinary, Numeric, String
from sqlalchemy.sql.sqltypes import NullType

from pyingestkit.dataset import Dataset

from .errors import TargetConfigurationError


class PostgresValueType(StrEnum):
    """Internal deterministic logical types used by the PostgreSQL target mapper."""

    TEXT = "TEXT"
    BIGINT = "BIGINT"
    DOUBLE_PRECISION = "DOUBLE PRECISION"
    NUMERIC = "NUMERIC"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP WITHOUT TIME ZONE"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    BYTEA = "BYTEA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PostgresColumnPlan:
    name: str
    value_type: PostgresValueType
    nullable_in_dataset: bool


@dataclass(frozen=True, slots=True)
class PostgresSchemaPlan:
    columns: tuple[PostgresColumnPlan, ...]

    @property
    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


class PostgresSchemaMapper:
    """Infer a deterministic PostgreSQL-oriented type plan from framework Dataset values.

    This mapper is deliberately not a schema migration engine. It validates a Dataset
    against an existing destination table and leaves DDL evolution out of V0.5.0-a2.
    """

    def plan(self, dataset: Dataset) -> PostgresSchemaPlan:
        columns = tuple(self._plan_column(dataset, field) for field in dataset.fields)
        return PostgresSchemaPlan(columns=columns)

    def validate_table(self, plan: PostgresSchemaPlan, table: Any) -> None:
        table_columns = {column.name: column for column in table.columns}
        unknown = set(plan.column_names).difference(table_columns)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise TargetConfigurationError(
                f"Dataset fields are absent from PostgreSQL destination: {names}"
            )

        mismatches: list[str] = []
        for column_plan in plan.columns:
            if column_plan.value_type is PostgresValueType.UNKNOWN:
                continue
            destination = table_columns[column_plan.name]
            if not self._is_compatible(column_plan.value_type, destination.type):
                mismatches.append(
                    f"{column_plan.name}: dataset={column_plan.value_type.value}, "
                    f"destination={destination.type}"
                )
        if mismatches:
            detail = "; ".join(mismatches)
            raise TargetConfigurationError(f"PostgreSQL destination schema mismatch: {detail}")

    def _plan_column(self, dataset: Dataset, field: str) -> PostgresColumnPlan:
        values: list[Any] = []
        nullable = False
        for row in dataset:
            if field not in row or row[field] is None:
                nullable = True
                continue
            values.append(row[field])
        value_type = self._infer_values(field, values)
        return PostgresColumnPlan(
            name=field,
            value_type=value_type,
            nullable_in_dataset=nullable,
        )

    def _infer_values(self, field: str, values: list[Any]) -> PostgresValueType:
        if not values:
            return PostgresValueType.UNKNOWN

        inferred = {self._infer_one(field, value) for value in values}
        if len(inferred) == 1:
            return next(iter(inferred))

        # Integer + float has one deterministic, loss-tolerant SQL representation.
        if inferred == {PostgresValueType.BIGINT, PostgresValueType.DOUBLE_PRECISION}:
            return PostgresValueType.DOUBLE_PRECISION

        names = ", ".join(sorted(item.value for item in inferred))
        raise TargetConfigurationError(
            f"Dataset field {field!r} has incompatible PostgreSQL value types: {names}"
        )

    def _infer_one(self, field: str, value: Any) -> PostgresValueType:
        if isinstance(value, bool):
            return PostgresValueType.BOOLEAN
        if isinstance(value, int):
            return PostgresValueType.BIGINT
        if isinstance(value, float):
            return PostgresValueType.DOUBLE_PRECISION
        if isinstance(value, Decimal):
            return PostgresValueType.NUMERIC
        if isinstance(value, str):
            return PostgresValueType.TEXT
        if isinstance(value, datetime):
            if value.tzinfo is not None and value.utcoffset() is not None:
                return PostgresValueType.TIMESTAMPTZ
            return PostgresValueType.TIMESTAMP
        if isinstance(value, date):
            return PostgresValueType.DATE
        if isinstance(value, (bytes, bytearray, memoryview)):
            return PostgresValueType.BYTEA
        raise TargetConfigurationError(
            f"Dataset field {field!r} contains unsupported PostgreSQL value type "
            f"{type(value).__name__!r}; nested mappings/lists require an explicit future mapping"
        )

    @staticmethod
    def _is_compatible(value_type: PostgresValueType, sql_type: Any) -> bool:
        if isinstance(sql_type, NullType):
            return False
        if value_type is PostgresValueType.TEXT:
            return isinstance(sql_type, String)
        if value_type is PostgresValueType.BIGINT:
            return isinstance(sql_type, Integer)
        if value_type is PostgresValueType.DOUBLE_PRECISION:
            return isinstance(sql_type, (Float, Numeric))
        if value_type is PostgresValueType.NUMERIC:
            return isinstance(sql_type, Numeric) and not isinstance(sql_type, Float)
        if value_type is PostgresValueType.BOOLEAN:
            return isinstance(sql_type, Boolean)
        if value_type is PostgresValueType.DATE:
            return isinstance(sql_type, Date) and not isinstance(sql_type, DateTime)
        if value_type is PostgresValueType.TIMESTAMP:
            return isinstance(sql_type, DateTime) and not bool(sql_type.timezone)
        if value_type is PostgresValueType.TIMESTAMPTZ:
            return isinstance(sql_type, DateTime) and bool(sql_type.timezone)
        if value_type is PostgresValueType.BYTEA:
            return isinstance(sql_type, LargeBinary)
        return True
