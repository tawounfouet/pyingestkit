"""PostgreSQL schema planning for V2 decoded representations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, Float, Integer, Numeric, String
from sqlalchemy.sql.sqltypes import NullType

from pyingestkit.domain.decoding import (
    DecodedArray,
    DecodedObject,
    DecodedRepresentation,
)


class PostgresValueTypeV2(StrEnum):
    """Conservative PostgreSQL-oriented types supported by V2 decoding."""

    TEXT = "TEXT"
    BIGINT = "BIGINT"
    DOUBLE_PRECISION = "DOUBLE PRECISION"
    BOOLEAN = "BOOLEAN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class PostgresColumnPlanV2:
    name: str
    value_type: PostgresValueTypeV2
    nullable: bool


@dataclass(frozen=True, slots=True)
class PostgresSchemaPlanV2:
    columns: tuple[PostgresColumnPlanV2, ...]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


class PostgresSchemaMapperV2:
    """Plan/validate existing PostgreSQL tables without performing DDL."""

    def plan(
        self,
        representation: DecodedRepresentation,
        columns: tuple[str, ...],
    ) -> PostgresSchemaPlanV2:
        return PostgresSchemaPlanV2(
            columns=tuple(self._plan_column(representation, column) for column in columns)
        )

    def validate_table(self, plan: PostgresSchemaPlanV2, table: Any) -> None:
        destination = {column.name: column for column in table.columns}
        missing = set(plan.names).difference(destination)
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Decoded fields are absent from PostgreSQL destination: {names}")

        mismatches: list[str] = []
        for column in plan.columns:
            if column.value_type is PostgresValueTypeV2.UNKNOWN:
                continue
            sql_column = destination[column.name]
            if not self._compatible(column.value_type, sql_column.type):
                mismatches.append(
                    f"{column.name}: decoded={column.value_type.value}, "
                    f"destination={sql_column.type}"
                )
        if mismatches:
            raise ValueError("PostgreSQL destination schema mismatch: " + "; ".join(mismatches))

    def _plan_column(
        self,
        representation: DecodedRepresentation,
        name: str,
    ) -> PostgresColumnPlanV2:
        values: list[object] = []
        nullable = False
        for record in representation.records:
            try:
                value = record.get(name)
            except KeyError:
                nullable = True
                continue
            if value is None:
                nullable = True
                continue
            values.append(value)

        return PostgresColumnPlanV2(
            name=name,
            value_type=self._infer_values(name, values),
            nullable=nullable,
        )

    def _infer_values(
        self,
        field: str,
        values: list[object],
    ) -> PostgresValueTypeV2:
        if not values:
            return PostgresValueTypeV2.UNKNOWN
        inferred = {self._infer_one(field, value) for value in values}
        if len(inferred) == 1:
            return next(iter(inferred))
        if inferred == {
            PostgresValueTypeV2.BIGINT,
            PostgresValueTypeV2.DOUBLE_PRECISION,
        }:
            return PostgresValueTypeV2.DOUBLE_PRECISION
        kinds = ", ".join(sorted(item.value for item in inferred))
        raise ValueError(
            f"Decoded field {field!r} has incompatible PostgreSQL value types: {kinds}"
        )

    @staticmethod
    def _infer_one(field: str, value: object) -> PostgresValueTypeV2:
        if isinstance(value, (DecodedObject, DecodedArray)):
            raise ValueError(
                f"Decoded field {field!r} contains a nested value; "
                "explicit JSON mapping is required."
            )
        if isinstance(value, bool):
            return PostgresValueTypeV2.BOOLEAN
        if isinstance(value, int):
            return PostgresValueTypeV2.BIGINT
        if isinstance(value, float):
            return PostgresValueTypeV2.DOUBLE_PRECISION
        if isinstance(value, str):
            return PostgresValueTypeV2.TEXT
        raise ValueError(
            f"Decoded field {field!r} contains unsupported PostgreSQL value "
            f"type {type(value).__name__!r}."
        )

    @staticmethod
    def _compatible(value_type: PostgresValueTypeV2, sql_type: Any) -> bool:
        if isinstance(sql_type, NullType):
            return False
        if value_type is PostgresValueTypeV2.TEXT:
            return isinstance(sql_type, String)
        if value_type is PostgresValueTypeV2.BIGINT:
            return isinstance(sql_type, Integer) and not isinstance(sql_type, Boolean)
        if value_type is PostgresValueTypeV2.DOUBLE_PRECISION:
            return isinstance(sql_type, (Float, Numeric))
        if value_type is PostgresValueTypeV2.BOOLEAN:
            return isinstance(sql_type, Boolean)
        return True
