from __future__ import annotations

import base64
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pyingestkit.core.exceptions import SnapshotError
from pyingestkit.dataset import Dataset
from pyingestkit.versioning._canonical import MISSING, canonical_value
from pyingestkit.versioning.fingerprint import DatasetFingerprinter


class SnapshotCodec:
    """Versioned, JSON-safe, type-aware Dataset snapshot codec.

    Snapshots preserve values because they are recovery/version artifacts, not
    redacted reports. They must therefore be protected like source data.
    """

    SNAPSHOT_VERSION = "1"

    def encode(self, dataset: Dataset) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        try:
            for row in dataset:
                rows.append(
                    {
                        field: canonical_value(row[field] if field in row else MISSING)
                        for field in dataset.fields
                    }
                )
        except TypeError as exc:
            raise SnapshotError(str(exc)) from exc
        return {
            "snapshot_version": self.SNAPSHOT_VERSION,
            "dataset": {"fields": list(dataset.fields), "rows": rows},
        }

    def decode(
        self, payload: Mapping[str, Any], *, source_artifact_id: str | None = None
    ) -> Dataset:
        if payload.get("snapshot_version") != self.SNAPSHOT_VERSION:
            raise SnapshotError(
                f"Unsupported snapshot_version: {payload.get('snapshot_version')!r}"
            )
        dataset_payload = payload.get("dataset")
        if not isinstance(dataset_payload, Mapping):
            raise SnapshotError("Snapshot dataset payload must be an object")
        fields_raw = dataset_payload.get("fields")
        rows_raw = dataset_payload.get("rows")
        if not isinstance(fields_raw, list) or not all(isinstance(v, str) for v in fields_raw):
            raise SnapshotError("Snapshot fields must be a list of strings")
        fields = tuple(fields_raw)
        if len(fields) != len(set(fields)):
            raise SnapshotError("Snapshot fields must be unique")
        if not isinstance(rows_raw, list):
            raise SnapshotError("Snapshot rows must be a list")
        rows: list[dict[str, Any]] = []
        for index, encoded_row in enumerate(rows_raw):
            if not isinstance(encoded_row, Mapping):
                raise SnapshotError(f"Snapshot row {index} must be an object")
            if set(encoded_row) != set(fields):
                raise SnapshotError(f"Snapshot row {index} does not match declared fields")
            row: dict[str, Any] = {}
            for field in fields:
                value = self._decode_value(encoded_row[field])
                if value is not MISSING:
                    row[field] = value
            rows.append(row)
        return Dataset(rows, fields=fields, source_artifact_id=source_artifact_id)

    def verify(self, dataset: Dataset, expected_fingerprint: str) -> None:
        actual = DatasetFingerprinter().fingerprint(dataset).id
        if actual != expected_fingerprint:
            raise SnapshotError(
                f"Snapshot fingerprint mismatch: expected {expected_fingerprint}, got {actual}"
            )

    def _decode_value(self, encoded: Any) -> Any:
        if not isinstance(encoded, Mapping):
            raise SnapshotError("Encoded snapshot value must be an object")
        tag = encoded.get("$type")
        try:
            if tag == "missing":
                return MISSING
            if tag == "none":
                return None
            if tag == "bool":
                value = encoded.get("value")
                if not isinstance(value, bool):
                    raise SnapshotError("Invalid bool snapshot value")
                return value
            if tag == "int":
                return int(str(encoded.get("value")))
            if tag == "float":
                value = str(encoded.get("value"))
                if value == "nan":
                    return float("nan")
                if value == "+inf":
                    return float("inf")
                if value == "-inf":
                    return float("-inf")
                return float.fromhex(value)
            if tag == "str":
                value = encoded.get("value")
                if not isinstance(value, str):
                    raise SnapshotError("Invalid str snapshot value")
                return value
            if tag == "bytes":
                if encoded.get("encoding") != "base64":
                    raise SnapshotError("Unsupported bytes snapshot encoding")
                return base64.b64decode(str(encoded.get("value")), validate=True)
            if tag == "decimal":
                return Decimal(str(encoded.get("value")))
            if tag == "date":
                return date.fromisoformat(str(encoded.get("value")))
            if tag == "datetime":
                return datetime.fromisoformat(str(encoded.get("value")))
            if tag in {"list", "tuple"}:
                items = encoded.get("items")
                if not isinstance(items, list):
                    raise SnapshotError(f"Invalid {tag} snapshot value")
                values = [self._decode_value(item) for item in items]
                if any(item is MISSING for item in values):
                    raise SnapshotError("Missing marker is only valid for dataset fields")
                return values if tag == "list" else tuple(values)
            if tag == "mapping":
                items = encoded.get("items")
                if not isinstance(items, list):
                    raise SnapshotError("Invalid mapping snapshot value")
                result: dict[Any, Any] = {}
                for pair in items:
                    if not isinstance(pair, list) or len(pair) != 2:
                        raise SnapshotError("Invalid mapping snapshot entry")
                    key = self._decode_value(pair[0])
                    value = self._decode_value(pair[1])
                    if key is MISSING or value is MISSING:
                        raise SnapshotError("Missing marker is only valid for dataset fields")
                    result[key] = value
                return result
        except (ValueError, TypeError, OverflowError) as exc:
            if isinstance(exc, SnapshotError):
                raise
            raise SnapshotError(f"Invalid {tag!r} snapshot value") from exc
        raise SnapshotError(f"Unsupported snapshot value tag: {tag!r}")
