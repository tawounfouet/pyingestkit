from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pyingestkit.diff.models import DatasetDiff, DiffEntry

_SECRET_FIELD = re.compile(
    r"(?:password|passwd|secret|token|api[_-]?key|authorization|cookie|credential)",
    re.IGNORECASE,
)
_STRING_LIMIT = 160


def diff_report_payload(
    diff: DatasetDiff,
    *,
    run_id: str,
    job_id: str,
    step_name: str,
    dataset_id: str,
) -> dict[str, object]:
    """Build schema-v1 portable diff evidence without leaking full rows by default."""

    return {
        "report_version": "1",
        "kind": "diff",
        "run_id": run_id,
        "job_id": job_id,
        "step": step_name,
        "dataset_id": dataset_id,
        "previous_version_id": diff.previous_fingerprint.id,
        "candidate_fingerprint": diff.candidate_fingerprint.id,
        "policy": {
            "key_fields": list(diff.policy.key_fields),
            "ignore_fields": list(diff.policy.ignore_fields),
            "compare_fields": (
                None if diff.policy.compare_fields is None else list(diff.policy.compare_fields)
            ),
            "order_sensitive": diff.policy.order_sensitive,
            "max_entries": diff.policy.max_entries,
            "capture_values": diff.policy.capture_values,
        },
        "summary": {
            "added": diff.added_count,
            "removed": diff.removed_count,
            "changed": diff.changed_count,
            "unchanged": diff.unchanged_count,
        },
        "schema": diff.schema.as_dict(),
        "entries_truncated": diff.entries_truncated,
        "entries": [_entry_payload(diff, entry) for entry in diff.entries],
    }


def _entry_payload(diff: DatasetDiff, entry: DiffEntry) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": entry.kind.value,
        "key": _safe_key(diff.policy.key_fields, entry.key),
        "changed_fields": list(entry.changed_fields),
    }
    if diff.policy.capture_values:
        payload["before"] = _safe_row(entry.before)
        payload["after"] = _safe_row(entry.after)
    return payload


def _safe_key(fields: Sequence[str], key: tuple[Any, ...] | None) -> list[object] | None:
    if key is None:
        return None
    values: list[object] = []
    for index, value in enumerate(key):
        field = fields[index] if index < len(fields) else None
        values.append(_safe_value(value, field_name=field))
    return values


def _safe_row(row: Mapping[str, Any] | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {field: _safe_value(value, field_name=field) for field, value in row.items()}


def _safe_value(value: Any, *, field_name: str | None = None) -> object:
    if field_name is not None and _SECRET_FIELD.search(field_name):
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "+Infinity" if value > 0 else "-Infinity"
        if value == 0.0 and math.copysign(1.0, value) < 0:
            return "-0.0"
        return value
    if isinstance(value, str):
        return value if len(value) <= _STRING_LIMIT else value[: _STRING_LIMIT - 1] + "…"
    if isinstance(value, bytes):
        return {"type": "bytes", "size": len(value)}
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            label = str(key)
            result[label] = _safe_value(item, field_name=label)
        return result
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return {"type": type(value).__name__}
