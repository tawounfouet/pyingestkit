from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from pyingestkit.decoders import (
    CsvDecoder,
    CsvDecoderConfig,
    DecodeRequest,
    DecodeStatus,
    DecodedArray,
    DecodedObject,
    DecoderLimits,
    DecoderRegistry,
    JsonDecoder,
    JsonDecoderConfig,
    JsonMode,
)
from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.runtime import CorrelationContext, FailureCategory
from pyingestkit.domain.shared import IngestionRunId


def _request(content: bytes, *, media_type: str) -> DecodeRequest:
    run_id = IngestionRunId.new()
    checksum = hashlib.sha256(content).hexdigest()
    resource = ResourceReference(
        namespace="pyingestkit.artifact.file",
        resource_id="raw-test",
        locator="file:///tmp/raw-test",
        media_type=media_type,
    )
    artifact = ArtifactReference(
        artifact_id="raw-test",
        kind="raw",
        resource=resource,
        checksum=checksum,
        checksum_algorithm="sha256",
        media_type=media_type,
        size_bytes=len(content),
        created_at=datetime(2026, 10, 2, tzinfo=UTC),
    )
    return DecodeRequest(
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        artifact=artifact,
        content=content,
    )


def test_csv_decode_is_deterministic_and_string_typed() -> None:
    request = _request(b"id,name\n1,Ada\n2,Linus\n", media_type="text/csv")
    decoder = CsvDecoder()

    first = decoder.decode(request)
    second = decoder.decode(request)

    assert first == second
    assert first.status is DecodeStatus.SUCCEEDED
    assert first.row_count == 2
    assert first.representation is not None
    assert first.representation.records[0].get("id") == "1"
    assert first.representation.records[0].get("name") == "Ada"
    assert first.schema is not None
    assert [field.name for field in first.schema.fields] == ["id", "name"]
    assert all(field.observed_types[0].value == "string" for field in first.schema.fields)


def test_csv_headerless_columns_are_deterministic() -> None:
    result = CsvDecoder(CsvDecoderConfig(header=False)).decode(
        _request(b"1,Ada\n2,Linus\n", media_type="text/csv")
    )

    assert result.status is DecodeStatus.SUCCEEDED
    assert result.representation is not None
    assert result.representation.records[1].get("column_2") == "Linus"


@pytest.mark.parametrize(
    "content",
    [
        b"id,id\n1,2\n",
        b"id,\n1,2\n",
        b"id,name\n1\n",
    ],
)
def test_csv_malformed_structure_returns_failure(content: bytes) -> None:
    result = CsvDecoder().decode(_request(content, media_type="text/csv"))

    assert result.status is DecodeStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.VALIDATION


def test_csv_row_limit_is_structured_failure() -> None:
    decoder = CsvDecoder(
        CsvDecoderConfig(limits=DecoderLimits(max_rows=1))
    )
    result = decoder.decode(
        _request(b"id\n1\n2\n", media_type="text/csv")
    )

    assert result.status is DecodeStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.RESOURCE_EXHAUSTED


def test_csv_invalid_utf8_is_structured_failure() -> None:
    result = CsvDecoder().decode(_request(b"id\n\xff\n", media_type="text/csv"))

    assert result.status is DecodeStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.VALIDATION


def test_json_array_preserves_json_types_and_nested_values() -> None:
    content = (
        b'[{"id":1,"active":true,"profile":{"city":"Paris"},"tags":["a","b"]},'
        b'{"id":2,"active":false,"profile":null,"tags":[]}]'
    )
    result = JsonDecoder().decode(_request(content, media_type="application/json"))

    assert result.status is DecodeStatus.SUCCEEDED
    assert result.row_count == 2
    assert result.representation is not None
    first = result.representation.records[0]
    assert first.get("id") == 1
    assert first.get("active") is True
    assert isinstance(first.get("profile"), DecodedObject)
    assert isinstance(first.get("tags"), DecodedArray)
    assert result.schema is not None
    profile = next(field for field in result.schema.fields if field.name == "profile")
    assert profile.nullable is True


def test_jsonl_decoder_uses_stable_jsonl_id() -> None:
    decoder = JsonDecoder(JsonDecoderConfig(mode=JsonMode.NDJSON))
    content = b'{"id":1}\n{"id":2}\n'
    result = decoder.decode(_request(content, media_type="application/x-ndjson"))

    assert decoder.descriptor.id == "jsonl"
    assert result.status is DecodeStatus.SUCCEEDED
    assert result.row_count == 2


@pytest.mark.parametrize(
    "content",
    [
        b'{"id":1,"id":2}',
        b'[1,2,3]',
        b'{"score":NaN}',
        b'{"broken":',
    ],
)
def test_json_malformed_inputs_return_failure(content: bytes) -> None:
    result = JsonDecoder().decode(_request(content, media_type="application/json"))

    assert result.status is DecodeStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.VALIDATION


def test_json_nesting_limit_is_structured_failure() -> None:
    decoder = JsonDecoder(
        JsonDecoderConfig(limits=DecoderLimits(max_nesting_depth=2))
    )
    result = decoder.decode(
        _request(b'{"a":{"b":{"c":1}}}', media_type="application/json")
    )

    assert result.status is DecodeStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.RESOURCE_EXHAUSTED


def test_decode_verifies_artifact_integrity() -> None:
    request = _request(b"id\n1\n", media_type="text/csv")
    tampered = DecodeRequest(
        ingestion_run_id=request.ingestion_run_id,
        correlation=request.correlation,
        artifact=request.artifact,
        content=b"id\n2\n",
    )

    result = CsvDecoder().decode(tampered)

    assert result.status is DecodeStatus.FAILED
    assert result.failure is not None
    assert result.failure.category is FailureCategory.VALIDATION


def test_decoded_representation_is_immutable() -> None:
    result = CsvDecoder().decode(_request(b"id\n1\n", media_type="text/csv"))
    assert result.representation is not None

    with pytest.raises(FrozenInstanceError):
        result.representation.records = ()  # type: ignore[misc]


def test_decoder_registry_is_explicit_and_rejects_duplicates() -> None:
    registry = DecoderRegistry()
    registry.register(CsvDecoder())
    registry.register(JsonDecoder())
    registry.register(JsonDecoder(JsonDecoderConfig(mode=JsonMode.NDJSON)))

    assert [decoder.descriptor.id for decoder in registry.list()] == ["csv", "json", "jsonl"]
    assert registry.get("jsonl").descriptor.id == "jsonl"

    with pytest.raises(ValueError):
        registry.register(CsvDecoder())
