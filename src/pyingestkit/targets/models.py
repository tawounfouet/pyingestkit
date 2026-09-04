from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from pyingestkit.dataset import Dataset


class LoadMode(StrEnum):
    """Stable names for V0.5 load semantics; backend support is capability-driven."""

    APPEND = "append"
    TRUNCATE_LOAD = "truncate_load"
    REPLACE = "replace"


class TargetLoadStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SKIPPED = "SKIPPED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True, slots=True)
class TargetLoadRequest:
    """Framework-owned request to materialize one Dataset in one explicit target."""

    target_id: str
    dataset_id: str
    run_id: str
    dataset: Dataset
    table: str
    dataset_version_id: str | None = None
    mode: LoadMode = LoadMode.APPEND
    schema: str | None = None
    key_fields: tuple[str, ...] = ()
    expected_row_count: int | None = None
    options: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("target_id", self.target_id),
            ("dataset_id", self.dataset_id),
            ("run_id", self.run_id),
            ("table", self.table),
        ):
            if not value or not value.strip():
                raise ValueError(f"TargetLoadRequest.{name} must not be empty")
        if "://" in self.target_id:
            raise ValueError("TargetLoadRequest.target_id must be a stable logical id, not a DSN")
        if self.expected_row_count is not None and self.expected_row_count < 0:
            raise ValueError("TargetLoadRequest.expected_row_count must be >= 0 or None")
        keys = tuple(self.key_fields)
        if len(keys) != len(set(keys)):
            raise ValueError("TargetLoadRequest.key_fields must be unique")
        unknown = set(keys).difference(self.dataset.fields)
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"TargetLoadRequest.key_fields are not in the Dataset: {names}")
        object.__setattr__(self, "key_fields", keys)
        object.__setattr__(self, "options", MappingProxyType(dict(self.options)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class TargetLoadResult:
    """Portable result of one completed target-load attempt."""

    load_id: str
    target_id: str
    dataset_id: str
    run_id: str
    mode: LoadMode
    status: TargetLoadStatus
    rows_input: int
    rows_loaded: int
    rows_verified: int | None
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    destination: str
    dataset_version_id: str | None = None
    idempotency_action: str | None = None
    metrics: Mapping[str, int | float] = field(default_factory=dict)
    error: str | None = None

    def __post_init__(self) -> None:
        if self.rows_input < 0 or self.rows_loaded < 0:
            raise ValueError("TargetLoadResult row counts must be >= 0")
        if self.rows_verified is not None and self.rows_verified < 0:
            raise ValueError("TargetLoadResult.rows_verified must be >= 0 or None")
        if self.duration_seconds < 0:
            raise ValueError("TargetLoadResult.duration_seconds must be >= 0")
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))
