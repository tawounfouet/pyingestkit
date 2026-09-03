from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, overload


@dataclass(frozen=True, slots=True, init=False)
class Dataset:
    """Framework-owned, dependency-neutral tabular dataset.

    Dataset deliberately stores Python mappings and does not expose Pandas,
    Polars, Arrow, or dataframe-specific semantics. Parsers may construct it;
    business normalization remains a separate lifecycle concern.
    """

    rows: tuple[Mapping[str, Any], ...]
    fields: tuple[str, ...]
    source_artifact_id: str | None

    def __init__(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        fields: Iterable[str] | None = None,
        source_artifact_id: str | None = None,
    ) -> None:
        normalized_rows = tuple(MappingProxyType(dict(row)) for row in rows)
        normalized_fields = self._normalize_fields(normalized_rows, fields)
        field_set = set(normalized_fields)
        for index, row in enumerate(normalized_rows):
            unknown = set(row).difference(field_set)
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(f"Row {index} contains fields outside the dataset schema: {names}")
        object.__setattr__(self, "rows", normalized_rows)
        object.__setattr__(self, "fields", normalized_fields)
        object.__setattr__(self, "source_artifact_id", source_artifact_id)

    @staticmethod
    def _normalize_fields(
        rows: tuple[Mapping[str, Any], ...], fields: Iterable[str] | None
    ) -> tuple[str, ...]:
        if fields is None:
            ordered: list[str] = []
            seen: set[str] = set()
            for row in rows:
                for key in row:
                    if not isinstance(key, str):
                        raise TypeError("Dataset field names must be strings")
                    if key not in seen:
                        seen.add(key)
                        ordered.append(key)
            return tuple(ordered)

        normalized = tuple(fields)
        if any(not isinstance(field, str) for field in normalized):
            raise TypeError("Dataset field names must be strings")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Dataset field names must be unique")
        return normalized

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def to_rows(self) -> list[dict[str, Any]]:
        """Return mutable row copies at an explicit interoperability boundary."""

        return [dict(row) for row in self.rows]

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[Mapping[str, Any]]:
        return iter(self.rows)

    @overload
    def __getitem__(self, index: int) -> Mapping[str, Any]: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Mapping[str, Any]]: ...

    def __getitem__(
        self, index: int | slice
    ) -> Mapping[str, Any] | Sequence[Mapping[str, Any]]:
        return self.rows[index]
