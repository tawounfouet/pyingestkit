"""Shared helpers for bounded foundation decoders."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from pyingestkit.domain.decoding.models import (
    DecodeRequest,
    DecodeResult,
    DecodeStatus,
    DecodedArray,
    DecodedObject,
    DecodedRecord,
    DecodedRepresentation,
    DecodedType,
    DecodedValue,
    SchemaEvidence,
    SchemaFieldEvidence,
)
from pyingestkit.domain.decoding.policy import DecoderLimits, EncodingPolicy
from pyingestkit.domain.runtime.diagnostics import Diagnostic, DiagnosticSeverity
from pyingestkit.domain.runtime.failure import (
    FailureCategory,
    FailureEvidence,
    OutcomeUncertainty,
    Retryability,
)


class DecodeDataError(ValueError):
    """Malformed content that cannot satisfy one decoder contract."""


class DecodeLimitError(ValueError):
    """Content exceeded an explicit decoder resource bound."""


def decode_text(content: bytes, policy: EncodingPolicy, limits: DecoderLimits) -> str:
    if len(content) > limits.max_bytes:
        raise DecodeLimitError(
            f"Input exceeds max_bytes={limits.max_bytes}; actual={len(content)}."
        )
    encoding = policy.encoding
    if policy.allow_utf8_bom and encoding.lower().replace("_", "-") in {"utf-8", "utf8"}:
        encoding = "utf-8-sig"
    return content.decode(encoding, errors=policy.errors.value)


def validate_artifact_integrity(request: DecodeRequest) -> None:
    reference = request.artifact
    if reference.size_bytes is not None and reference.size_bytes != len(request.content):
        raise DecodeDataError("RAW byte size does not match ArtifactReference evidence.")
    if reference.checksum is not None:
        if reference.checksum_algorithm != "sha256":
            raise DecodeDataError("Foundation decoders require SHA-256 artifact evidence.")
        actual = hashlib.sha256(request.content).hexdigest()
        if actual != reference.checksum:
            raise DecodeDataError("RAW bytes do not match ArtifactReference SHA-256 evidence.")


def freeze_json_value(value: object, *, depth: int, limits: DecoderLimits) -> DecodedValue:
    if depth > limits.max_nesting_depth:
        raise DecodeLimitError(
            f"JSON nesting exceeds max_nesting_depth={limits.max_nesting_depth}."
        )
    if value is None or isinstance(value, bool | int | float | str):
        if isinstance(value, str) and len(value) > limits.max_field_chars:
            raise DecodeLimitError(
                f"JSON string exceeds max_field_chars={limits.max_field_chars}."
            )
        return value
    if isinstance(value, Mapping):
        if len(value) > limits.max_keys_per_object:
            raise DecodeLimitError(
                f"JSON object exceeds max_keys_per_object={limits.max_keys_per_object}."
            )
        return DecodedObject(
            tuple(
                (
                    str(key),
                    freeze_json_value(item, depth=depth + 1, limits=limits),
                )
                for key, item in value.items()
            )
        )
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return DecodedArray(
            tuple(freeze_json_value(item, depth=depth + 1, limits=limits) for item in value)
        )
    raise DecodeDataError(f"Unsupported JSON value type: {type(value).__name__}.")


def decoded_type(value: DecodedValue) -> DecodedType:
    if value is None:
        return DecodedType.NULL
    if isinstance(value, bool):
        return DecodedType.BOOLEAN
    if isinstance(value, int):
        return DecodedType.INTEGER
    if isinstance(value, float):
        return DecodedType.NUMBER
    if isinstance(value, str):
        return DecodedType.STRING
    if isinstance(value, DecodedObject):
        return DecodedType.OBJECT
    if isinstance(value, DecodedArray):
        return DecodedType.ARRAY
    raise TypeError(f"Unsupported decoded value: {type(value).__name__}.")


def build_schema(
    records: tuple[DecodedRecord, ...],
    *,
    preferred_order: tuple[str, ...] | None = None,
) -> SchemaEvidence:
    if preferred_order is None:
        names = sorted({name for record in records for name, _ in record.fields})
    else:
        names = list(preferred_order)

    evidence: list[SchemaFieldEvidence] = []
    total = len(records)
    for name in names:
        observed: set[DecodedType] = set()
        present = 0
        for record in records:
            values = {field_name: value for field_name, value in record.fields}
            if name in values:
                present += 1
                observed.add(decoded_type(values[name]))
        nullable = present < total or DecodedType.NULL in observed
        if not observed:
            observed.add(DecodedType.NULL)
            nullable = True
        ordered_types = tuple(sorted(observed, key=lambda value: value.value))
        evidence.append(
            SchemaFieldEvidence(
                name=name,
                observed_types=ordered_types,
                nullable=nullable,
            )
        )
    return SchemaEvidence(tuple(evidence))


def success_result(
    request: DecodeRequest,
    *,
    decoder_id: str,
    decoder_version: str,
    records: tuple[DecodedRecord, ...],
    schema: SchemaEvidence,
) -> DecodeResult:
    representation = DecodedRepresentation(records)
    diagnostic = Diagnostic(
        code="decode.succeeded",
        severity=DiagnosticSeverity.INFO,
        summary="Input bytes were decoded successfully.",
        stage="decode",
        source_context=decoder_id,
        details=(("row_count", str(len(records))),),
        ingestion_run_id=request.ingestion_run_id,
        correlation_id=request.correlation.correlation_id,
    )
    return DecodeResult(
        status=DecodeStatus.SUCCEEDED,
        ingestion_run_id=request.ingestion_run_id,
        correlation=request.correlation,
        decoder_id=decoder_id,
        decoder_version=decoder_version,
        representation=representation,
        schema=schema,
        row_count=len(records),
        diagnostics=(diagnostic,),
    )


def failure_result(
    request: DecodeRequest,
    *,
    decoder_id: str,
    decoder_version: str,
    error_code: str,
    category: FailureCategory,
    summary: str,
) -> DecodeResult:
    failure = FailureEvidence(
        error_code=error_code,
        category=category,
        retryability=Retryability.NON_RETRYABLE,
        uncertainty=OutcomeUncertainty.KNOWN,
        ingestion_run_id=request.ingestion_run_id,
        correlation_id=request.correlation.correlation_id,
        source_component=decoder_id,
        message_summary=summary,
    )
    diagnostic = Diagnostic(
        code=error_code,
        severity=DiagnosticSeverity.ERROR,
        summary=summary,
        stage="decode",
        source_context=decoder_id,
        ingestion_run_id=request.ingestion_run_id,
        correlation_id=request.correlation.correlation_id,
    )
    return DecodeResult(
        status=DecodeStatus.FAILED,
        ingestion_run_id=request.ingestion_run_id,
        correlation=request.correlation,
        decoder_id=decoder_id,
        decoder_version=decoder_version,
        diagnostics=(diagnostic,),
        failure=failure,
    )
