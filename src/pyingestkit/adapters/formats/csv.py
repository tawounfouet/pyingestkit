"""Bounded standard-library CSV decoder."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from itertools import chain

from pyingestkit.domain.decoding.models import (
    DecodedRecord,
    DecodedRepresentation,
    DecodeRequest,
    DecodeResult,
    SchemaEvidence,
)
from pyingestkit.domain.decoding.policy import DecoderLimits, EncodingPolicy
from pyingestkit.domain.runtime.failure import FailureCategory
from pyingestkit.ports.decoders import (
    DecoderCapability,
    DecoderDescriptor,
)

from ._common import (
    DecodeDataError,
    DecodeLimitError,
    build_schema,
    decode_text,
    failure_result,
    success_result,
    validate_artifact_integrity,
)


@dataclass(frozen=True, slots=True)
class CsvDecoderConfig:
    """Portable CSV foundation configuration."""

    delimiter: str = ","
    header: bool = True
    quotechar: str = '"'
    escapechar: str | None = None
    encoding: EncodingPolicy = field(default_factory=EncodingPolicy)
    limits: DecoderLimits = field(default_factory=DecoderLimits)

    def __post_init__(self) -> None:
        _one_character(self.delimiter, "CsvDecoderConfig delimiter")
        _one_character(self.quotechar, "CsvDecoderConfig quotechar")
        if self.escapechar is not None:
            _one_character(self.escapechar, "CsvDecoderConfig escapechar")
        if not isinstance(self.header, bool):
            raise TypeError("CsvDecoderConfig header must be bool.")
        if not isinstance(self.encoding, EncodingPolicy):
            raise TypeError("CsvDecoderConfig encoding must be EncodingPolicy.")
        if not isinstance(self.limits, DecoderLimits):
            raise TypeError("CsvDecoderConfig limits must be DecoderLimits.")


class CsvDecoder:
    """Decode CSV bytes into immutable string-valued records."""

    def __init__(self, config: CsvDecoderConfig | None = None) -> None:
        self._config = config or CsvDecoderConfig()

    @property
    def config(self) -> CsvDecoderConfig:
        return self._config

    @property
    def descriptor(self) -> DecoderDescriptor:
        return DecoderDescriptor(
            id="csv",
            display_name="CSV",
            decoder_version="1",
            media_types=("text/csv", "application/csv"),
            formats=("csv",),
            capabilities=(
                DecoderCapability.ROW_COUNT,
                DecoderCapability.SCHEMA_EVIDENCE,
            ),
            configuration_fields=(
                "delimiter",
                "header",
                "quotechar",
                "escapechar",
                "encoding",
                "limits",
            ),
        )

    def decode(self, request: DecodeRequest) -> DecodeResult:
        try:
            validate_artifact_integrity(request)
            representation, schema = _decode_csv_bytes(request.content, self._config)
            records = representation.records
            return success_result(
                request,
                decoder_id=self.descriptor.id,
                decoder_version=self.descriptor.decoder_version,
                records=records,
                schema=schema,
            )
        except DecodeLimitError as exc:
            return failure_result(
                request,
                decoder_id=self.descriptor.id,
                decoder_version=self.descriptor.decoder_version,
                error_code="decode.csv.resource_limit",
                category=FailureCategory.RESOURCE_EXHAUSTED,
                summary=str(exc),
            )
        except (DecodeDataError, UnicodeDecodeError, csv.Error) as exc:
            return failure_result(
                request,
                decoder_id=self.descriptor.id,
                decoder_version=self.descriptor.decoder_version,
                error_code="decode.csv.invalid_input",
                category=FailureCategory.VALIDATION,
                summary=str(exc),
            )


def _decode_csv_bytes(
    content: bytes,
    config: CsvDecoderConfig,
) -> tuple[DecodedRepresentation, SchemaEvidence]:
    text = decode_text(content, config.encoding, config.limits)
    records, headers = _parse_csv_text(text, config)
    return (
        DecodedRepresentation(records=records),
        build_schema(records, preferred_order=headers),
    )


def _parse_csv_text(
    text: str,
    config: CsvDecoderConfig,
) -> tuple[tuple[DecodedRecord, ...], tuple[str, ...]]:
    reader = csv.reader(
        io.StringIO(text, newline=""),
        delimiter=config.delimiter,
        quotechar=config.quotechar,
        escapechar=config.escapechar,
        strict=True,
    )
    try:
        first = next(reader)
    except StopIteration:
        return (), ()

    if config.header:
        headers = tuple(first)
        _validate_headers(headers, config.limits)
    else:
        _validate_row_width(first, config.limits)
        headers = tuple(f"column_{index}" for index in range(1, len(first) + 1))

    rows: list[DecodedRecord] = []
    initial_rows = () if config.header else (first,)
    for row in chain(initial_rows, reader):
        _validate_row(row, headers, config.limits)
        rows.append(
            DecodedRecord(
                tuple((name, value) for name, value in zip(headers, row, strict=True))
            )
        )
        if len(rows) > config.limits.max_rows:
            raise DecodeLimitError(f"CSV exceeds max_rows={config.limits.max_rows}.")
    return tuple(rows), headers

def _one_character(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 1:
        raise ValueError(f"{name} must be exactly one character.")


def _validate_headers(headers: tuple[str, ...], limits: DecoderLimits) -> None:
    if not headers:
        raise DecodeDataError("CSV header row must contain at least one field.")
    _validate_row_width(headers, limits)
    if any(not name.strip() for name in headers):
        raise DecodeDataError("CSV header names must be non-blank.")
    if len(set(headers)) != len(headers):
        raise DecodeDataError("CSV header names must be unique.")
    for name in headers:
        if len(name) > limits.max_field_chars:
            raise DecodeLimitError(f"CSV header exceeds max_field_chars={limits.max_field_chars}.")


def _validate_row_width(row: list[str] | tuple[str, ...], limits: DecoderLimits) -> None:
    if len(row) > limits.max_columns:
        raise DecodeLimitError(f"CSV exceeds max_columns={limits.max_columns}; actual={len(row)}.")


def _validate_row(row: list[str], headers: tuple[str, ...], limits: DecoderLimits) -> None:
    _validate_row_width(row, limits)
    if len(row) != len(headers):
        raise DecodeDataError(
            f"CSV row width {len(row)} does not match expected width {len(headers)}."
        )
    for value in row:
        if len(value) > limits.max_field_chars:
            raise DecodeLimitError(f"CSV field exceeds max_field_chars={limits.max_field_chars}.")
