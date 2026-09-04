from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from pyingestkit.dataset import Dataset

from .models import DatasetProfile, FieldProfile

_MISSING = object()


def _stable_identity(value: Any) -> object:
    if value is _MISSING:
        return ("missing",)
    if value is None or isinstance(value, (str, int, float, bool, bytes)):
        return (type(value).__name__, value)
    if isinstance(value, tuple):
        return ("tuple", tuple(_stable_identity(item) for item in value))
    if isinstance(value, list):
        return ("list", tuple(_stable_identity(item) for item in value))
    if isinstance(value, Mapping):
        return (
            "mapping",
            tuple(
                sorted(
                    ((str(key), _stable_identity(item)) for key, item in value.items()),
                    key=lambda pair: pair[0],
                )
            ),
        )
    if isinstance(value, (set, frozenset)):
        frozen = [_stable_identity(item) for item in value]
        return ("set", tuple(sorted(frozen, key=repr)))
    try:
        hash(value)
    except TypeError:
        return (type(value).__name__, repr(value))
    return (type(value).__name__, value)


def _observed_type_name(value: Any) -> str:
    return type(value).__name__


class DatasetProfiler:
    """Describe a materialized Dataset without semantic inference or mutation."""

    def profile(self, dataset: Dataset) -> DatasetProfile:
        started_at = datetime.now(UTC)
        started_clock = perf_counter()
        fields = tuple(self._profile_field(dataset, name) for name in dataset.fields)
        duplicate_row_count = self._duplicate_row_count(dataset)
        return DatasetProfile(
            row_count=dataset.row_count,
            field_count=len(dataset.fields),
            fields=fields,
            duplicate_row_count=duplicate_row_count,
            source_artifact_id=dataset.source_artifact_id,
            generated_at=started_at,
            duration_ms=(perf_counter() - started_clock) * 1000.0,
        )

    @staticmethod
    def _profile_field(dataset: Dataset, name: str) -> FieldProfile:
        present_values = [row[name] for row in dataset if name in row]
        non_null_values = [value for value in present_values if value is not None]
        observed_types = tuple(sorted({_observed_type_name(value) for value in present_values}))
        identities = {_stable_identity(value) for value in non_null_values}

        string_values = [value for value in non_null_values if isinstance(value, str)]
        if string_values and len(string_values) == len(non_null_values):
            lengths = [len(value) for value in string_values]
            min_length = min(lengths)
            max_length = max(lengths)
        else:
            min_length = None
            max_length = None

        numeric_values = [
            value
            for value in non_null_values
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        if numeric_values and len(numeric_values) == len(non_null_values):
            min_value: int | float | None = min(numeric_values)
            max_value: int | float | None = max(numeric_values)
        else:
            min_value = None
            max_value = None

        return FieldProfile(
            name=name,
            present_count=len(present_values),
            null_count=sum(value is None for value in present_values),
            non_null_count=len(non_null_values),
            distinct_count=len(identities),
            observed_types=observed_types,
            min_length=min_length,
            max_length=max_length,
            min_value=min_value,
            max_value=max_value,
        )

    @staticmethod
    def _duplicate_row_count(dataset: Dataset) -> int:
        seen: set[tuple[object, ...]] = set()
        duplicates = 0
        for row in dataset:
            identity = tuple(
                _stable_identity(row[field] if field in row else _MISSING)
                for field in dataset.fields
            )
            if identity in seen:
                duplicates += 1
            else:
                seen.add(identity)
        return duplicates
