from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


@dataclass(frozen=True, slots=True)
class FieldProfile:
    name: str
    present_count: int
    null_count: int
    non_null_count: int
    distinct_count: int
    observed_types: tuple[str, ...]
    min_length: int | None = None
    max_length: int | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "present_count": self.present_count,
            "null_count": self.null_count,
            "non_null_count": self.non_null_count,
            "distinct_count": self.distinct_count,
            "observed_types": list(self.observed_types),
            "min_length": self.min_length,
            "max_length": self.max_length,
            "min_value": _json_value(self.min_value),
            "max_value": _json_value(self.max_value),
        }


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    row_count: int
    field_count: int
    fields: tuple[FieldProfile, ...]
    duplicate_row_count: int
    source_artifact_id: str | None = None
    generated_at: datetime | None = None
    duration_ms: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "row_count": self.row_count,
            "field_count": self.field_count,
            "fields": [field.as_dict() for field in self.fields],
            "duplicate_row_count": self.duplicate_row_count,
            "source_artifact_id": self.source_artifact_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "duration_ms": self.duration_ms,
        }
