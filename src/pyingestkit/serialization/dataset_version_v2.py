"""Portable LOT-08 dataset-version snapshot codec."""

from __future__ import annotations

import json

from pyingestkit.domain.datasets.version import DatasetVersion
from pyingestkit.domain.decoding.models import (
    DecodedArray,
    DecodedObject,
    DecodedRecord,
    DecodedRepresentation,
    DecodedType,
    DecodedValue,
    SchemaEvidence,
    SchemaFieldEvidence,
)


def encode_dataset_snapshot(version: DatasetVersion) -> bytes:
    """Encode one logical dataset version into deterministic portable JSON bytes."""
    if not isinstance(version, DatasetVersion):
        raise TypeError("encode_dataset_snapshot requires DatasetVersion.")

    payload = {
        "snapshot_version": "1",
        "dataset_id": version.dataset_id,
        "version_id": version.version_id,
        "schema": {
            "fingerprint": version.schema.fingerprint,
            "fields": [
                {
                    "name": field.name,
                    "observed_types": [item.value for item in field.observed_types],
                    "nullable": field.nullable,
                }
                for field in version.schema.fields
            ],
        },
        "records": [
            [[name, _encode_value(value)] for name, value in record.fields]
            for record in version.representation.records
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def decode_dataset_snapshot(content: bytes) -> tuple[SchemaEvidence, DecodedRepresentation]:
    """Decode portable snapshot bytes back into framework-owned immutable values."""
    if not isinstance(content, bytes):
        raise TypeError("decode_dataset_snapshot content must be bytes.")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Dataset snapshot is not valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict) or payload.get("snapshot_version") != "1":
        raise ValueError("Unsupported dataset snapshot contract.")

    raw_schema = payload.get("schema")
    raw_records = payload.get("records")
    if not isinstance(raw_schema, dict) or not isinstance(raw_records, list):
        raise ValueError("Dataset snapshot is missing schema or records.")

    raw_fields = raw_schema.get("fields")
    if not isinstance(raw_fields, list):
        raise ValueError("Dataset snapshot schema fields must be a list.")

    fields: list[SchemaFieldEvidence] = []
    for raw_field in raw_fields:
        if not isinstance(raw_field, dict):
            raise ValueError("Dataset snapshot schema field must be an object.")
        raw_types = raw_field.get("observed_types")
        if not isinstance(raw_types, list):
            raise ValueError("Dataset snapshot observed_types must be a list.")
        fields.append(
            SchemaFieldEvidence(
                name=str(raw_field["name"]),
                observed_types=tuple(DecodedType(str(item)) for item in raw_types),
                nullable=bool(raw_field["nullable"]),
            )
        )
    schema = SchemaEvidence(fields=tuple(fields))
    if raw_schema.get("fingerprint") != schema.fingerprint:
        raise ValueError("Dataset snapshot schema fingerprint mismatch.")

    records: list[DecodedRecord] = []
    for raw_record in raw_records:
        if not isinstance(raw_record, list):
            raise ValueError("Dataset snapshot record must be a list.")
        pairs: list[tuple[str, DecodedValue]] = []
        for raw_pair in raw_record:
            if not isinstance(raw_pair, list) or len(raw_pair) != 2:
                raise ValueError("Dataset snapshot record field must be a key/value pair.")
            name, raw_value = raw_pair
            if not isinstance(name, str):
                raise ValueError("Dataset snapshot record field name must be text.")
            pairs.append((name, _decode_value(raw_value)))
        records.append(DecodedRecord(fields=tuple(pairs)))

    return schema, DecodedRepresentation(records=tuple(records))


def _encode_value(value: DecodedValue) -> object:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        return {"type": "number", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, DecodedObject):
        return {
            "type": "object",
            "items": [[name, _encode_value(item)] for name, item in value.items],
        }
    if isinstance(value, DecodedArray):
        return {"type": "array", "items": [_encode_value(item) for item in value.items]}
    raise TypeError(f"Unsupported decoded value type: {type(value).__name__}.")


def _decode_value(payload: object) -> DecodedValue:
    if not isinstance(payload, dict):
        raise ValueError("Dataset snapshot value must be a typed object.")
    kind = payload.get("type")
    if kind == "null":
        return None
    value = payload.get("value")
    if kind == "boolean":
        if not isinstance(value, bool):
            raise ValueError("Boolean snapshot value must be bool.")
        return value
    if kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("Integer snapshot value must be int.")
        return value
    if kind == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("Number snapshot value must be numeric.")
        return float(value)
    if kind == "string":
        if not isinstance(value, str):
            raise ValueError("String snapshot value must be text.")
        return value
    if kind == "object":
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("Object snapshot items must be a list.")
        items: list[tuple[str, DecodedValue]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, list) or len(raw_item) != 2:
                raise ValueError("Object snapshot item must be a key/value pair.")
            name, nested = raw_item
            if not isinstance(name, str):
                raise ValueError("Object snapshot key must be text.")
            items.append((name, _decode_value(nested)))
        return DecodedObject(items=tuple(items))
    if kind == "array":
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise ValueError("Array snapshot items must be a list.")
        return DecodedArray(items=tuple(_decode_value(item) for item in raw_items))
    raise ValueError(f"Unsupported dataset snapshot value type: {kind!r}.")
