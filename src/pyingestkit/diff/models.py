from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from pyingestkit.versioning import DatasetFingerprint


class DiffKind(StrEnum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"


@dataclass(frozen=True, slots=True)
class DiffPolicy:
    key_fields: tuple[str, ...] = ()
    ignore_fields: tuple[str, ...] = ()
    compare_fields: tuple[str, ...] | None = None
    order_sensitive: bool = False
    max_entries: int | None = 1000
    capture_values: bool = False

    def __post_init__(self) -> None:
        key_fields = tuple(self.key_fields)
        ignore_fields = tuple(self.ignore_fields)
        compare_fields = None if self.compare_fields is None else tuple(self.compare_fields)
        for name, values in (("key_fields", key_fields), ("ignore_fields", ignore_fields)):
            if any(not field for field in values):
                raise ValueError(f"DiffPolicy.{name} field names must not be empty")
            if len(values) != len(set(values)):
                raise ValueError(f"DiffPolicy.{name} field names must be unique")
        if compare_fields is not None:
            if not compare_fields:
                raise ValueError("DiffPolicy.compare_fields must not be empty when provided")
            if any(not field for field in compare_fields):
                raise ValueError("DiffPolicy.compare_fields field names must not be empty")
            if len(compare_fields) != len(set(compare_fields)):
                raise ValueError("DiffPolicy.compare_fields field names must be unique")
            if ignore_fields:
                raise ValueError(
                    "DiffPolicy.ignore_fields and compare_fields are mutually exclusive"
                )
        if set(key_fields).intersection(ignore_fields):
            raise ValueError("DiffPolicy.key_fields must not be ignored")
        if compare_fields is not None and not set(key_fields).isdisjoint(compare_fields):
            raise ValueError("DiffPolicy.compare_fields must not repeat key fields")
        if self.max_entries is not None and self.max_entries <= 0:
            raise ValueError("DiffPolicy.max_entries must be > 0 or None")
        object.__setattr__(self, "key_fields", key_fields)
        object.__setattr__(self, "ignore_fields", ignore_fields)
        object.__setattr__(self, "compare_fields", compare_fields)


@dataclass(frozen=True, slots=True)
class SchemaDiff:
    added_fields: tuple[str, ...]
    removed_fields: tuple[str, ...]
    common_fields: tuple[str, ...]
    field_order_changed: bool

    @property
    def changed(self) -> bool:
        return bool(self.added_fields or self.removed_fields or self.field_order_changed)

    def as_dict(self) -> dict[str, object]:
        return {
            "added_fields": list(self.added_fields),
            "removed_fields": list(self.removed_fields),
            "common_fields": list(self.common_fields),
            "field_order_changed": self.field_order_changed,
        }


@dataclass(frozen=True, slots=True)
class DiffEntry:
    kind: DiffKind
    key: tuple[Any, ...] | None = None
    changed_fields: tuple[str, ...] = ()
    before: Mapping[str, Any] | None = None
    after: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.before is not None and not isinstance(self.before, MappingProxyType):
            object.__setattr__(self, "before", MappingProxyType(dict(self.before)))
        if self.after is not None and not isinstance(self.after, MappingProxyType):
            object.__setattr__(self, "after", MappingProxyType(dict(self.after)))


@dataclass(frozen=True, slots=True)
class DatasetDiff:
    previous_fingerprint: DatasetFingerprint
    candidate_fingerprint: DatasetFingerprint
    policy: DiffPolicy
    schema: SchemaDiff
    added_count: int
    removed_count: int
    changed_count: int
    unchanged_count: int
    entries: tuple[DiffEntry, ...]
    entries_truncated: bool = False

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_count
            or self.removed_count
            or self.changed_count
            or self.schema.changed
        )

    def as_dict(self, *, include_values: bool = False) -> dict[str, object]:
        return {
            "previous_fingerprint": self.previous_fingerprint.as_dict(),
            "candidate_fingerprint": self.candidate_fingerprint.as_dict(),
            "policy": {
                "key_fields": list(self.policy.key_fields),
                "ignore_fields": list(self.policy.ignore_fields),
                "compare_fields": (
                    None if self.policy.compare_fields is None else list(self.policy.compare_fields)
                ),
                "order_sensitive": self.policy.order_sensitive,
                "max_entries": self.policy.max_entries,
                "capture_values": self.policy.capture_values,
            },
            "schema": self.schema.as_dict(),
            "summary": {
                "added": self.added_count,
                "removed": self.removed_count,
                "changed": self.changed_count,
                "unchanged": self.unchanged_count,
            },
            "entries_truncated": self.entries_truncated,
            "entries": [
                self._entry_dict(entry, include_values=include_values) for entry in self.entries
            ],
        }

    @staticmethod
    def _entry_dict(entry: DiffEntry, *, include_values: bool) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": entry.kind.value,
            "key": None if entry.key is None else list(entry.key),
            "changed_fields": list(entry.changed_fields),
        }
        if include_values:
            result["before"] = None if entry.before is None else dict(entry.before)
            result["after"] = None if entry.after is None else dict(entry.after)
        return result
