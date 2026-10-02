"""Bounded JSON and JSON Lines decoder."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pyingestkit.domain.decoding.models import (
    DecodedRecord,
    DecodeRequest,
    DecodeResult,
)
from pyingestkit.domain.decoding.policy import DecoderLimits, EncodingPolicy
from pyingestkit.domain.runtime.failure import FailureCategory
from pyingestkit.ports.decoders import DecoderCapability, DecoderDescriptor

from ._common import (
    DecodeDataError,
    DecodeLimitError,
    build_schema,
    decode_text,
    failure_result,
    freeze_json_value,
    success_result,
    validate_artifact_integrity,
)


class JsonMode(StrEnum):
    JSON = "json"
    NDJSON = "jsonl"


@dataclass(frozen=True, slots=True)
class JsonDecoderConfig:
    """Portable JSON/JSONL foundation configuration."""

    mode: JsonMode = JsonMode.JSON
    encoding: EncodingPolicy = field(default_factory=EncodingPolicy)
    limits: DecoderLimits = field(default_factory=DecoderLimits)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, JsonMode):
            raise TypeError("JsonDecoderConfig mode must be JsonMode.")
        if not isinstance(self.encoding, EncodingPolicy):
            raise TypeError("JsonDecoderConfig encoding must be EncodingPolicy.")
        if not isinstance(self.limits, DecoderLimits):
            raise TypeError("JsonDecoderConfig limits must be DecoderLimits.")


class JsonDecoder:
    """Decode JSON objects/arrays or NDJSON object lines."""

    def __init__(self, config: JsonDecoderConfig | None = None) -> None:
        self._config = config or JsonDecoderConfig()

    @property
    def config(self) -> JsonDecoderConfig:
        return self._config

    @property
    def descriptor(self) -> DecoderDescriptor:
        decoder_id = self._config.mode.value
        formats = ("json",) if self._config.mode is JsonMode.JSON else ("jsonl", "ndjson")
        media_types = (
            ("application/json",)
            if self._config.mode is JsonMode.JSON
            else ("application/x-ndjson", "application/ndjson")
        )
        return DecoderDescriptor(
            id=decoder_id,
            display_name="JSON" if self._config.mode is JsonMode.JSON else "JSON Lines",
            decoder_version="1",
            media_types=media_types,
            formats=formats,
            capabilities=(
                DecoderCapability.ROW_COUNT,
                DecoderCapability.SCHEMA_EVIDENCE,
                DecoderCapability.NESTED_VALUES,
            ),
            configuration_fields=("mode", "encoding", "limits"),
        )

    def decode(self, request: DecodeRequest) -> DecodeResult:
        descriptor = self.descriptor
        try:
            validate_artifact_integrity(request)
            text = decode_text(request.content, self._config.encoding, self._config.limits)
            raw_records = self._parse(text)
            records = tuple(_freeze_record(record, self._config.limits) for record in raw_records)
            schema = build_schema(records)
            return success_result(
                request,
                decoder_id=descriptor.id,
                decoder_version=descriptor.decoder_version,
                records=records,
                schema=schema,
            )
        except DecodeLimitError as exc:
            return failure_result(
                request,
                decoder_id=descriptor.id,
                decoder_version=descriptor.decoder_version,
                error_code=f"decode.{descriptor.id}.resource_limit",
                category=FailureCategory.RESOURCE_EXHAUSTED,
                summary=str(exc),
            )
        except (DecodeDataError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return failure_result(
                request,
                decoder_id=descriptor.id,
                decoder_version=descriptor.decoder_version,
                error_code=f"decode.{descriptor.id}.invalid_input",
                category=FailureCategory.VALIDATION,
                summary=str(exc),
            )

    def _parse(self, text: str) -> tuple[dict[str, object], ...]:
        if self._config.mode is JsonMode.NDJSON:
            records: list[dict[str, object]] = []
            for line_number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                if len(line) > self._config.limits.max_field_chars:
                    raise DecodeLimitError(
                        f"JSONL line {line_number} exceeds max_field_chars="
                        f"{self._config.limits.max_field_chars}."
                    )
                value = _loads(line)
                if not isinstance(value, dict):
                    raise DecodeDataError(
                        f"JSONL line {line_number} must decode to an object."
                    )
                records.append(value)
                if len(records) > self._config.limits.max_rows:
                    raise DecodeLimitError(
                        f"JSONL exceeds max_rows={self._config.limits.max_rows}."
                    )
            return tuple(records)

        value = _loads(text)
        if isinstance(value, dict):
            return (value,)
        if isinstance(value, list):
            if len(value) > self._config.limits.max_rows:
                raise DecodeLimitError(
                    f"JSON array exceeds max_rows={self._config.limits.max_rows}."
                )
            if any(not isinstance(item, dict) for item in value):
                raise DecodeDataError("JSON array root must contain objects only.")
            return tuple(value)
        raise DecodeDataError("JSON root must be an object or an array of objects.")


def _loads(text: str) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise DecodeDataError(f"JSON object contains duplicate key {key!r}.")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise DecodeDataError(f"Non-standard JSON constant is not allowed: {value}.")

    return json.loads(
        text,
        object_pairs_hook=object_pairs,
        parse_constant=reject_constant,
    )


def _freeze_record(record: dict[str, object], limits: DecoderLimits) -> DecodedRecord:
    if len(record) > limits.max_columns:
        raise DecodeLimitError(
            f"JSON record exceeds max_columns={limits.max_columns}; actual={len(record)}."
        )
    fields = []
    for name, value in record.items():
        if not name.strip():
            raise DecodeDataError("JSON object field names must be non-blank.")
        if len(name) > limits.max_field_chars:
            raise DecodeLimitError(
                f"JSON field name exceeds max_field_chars={limits.max_field_chars}."
            )
        fields.append((name, freeze_json_value(value, depth=1, limits=limits)))
    return DecodedRecord(tuple(fields))
