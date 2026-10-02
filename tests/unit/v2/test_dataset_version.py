from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from pyingestkit.datasets import DatasetVersion, build_dataset_version
from pyingestkit.decoders import CsvDecoder, DecodeStatus

from .test_decoders import _request


def _version(content: bytes, *, dataset_id: str = "demo.reference") -> DatasetVersion:
    request = _request(content, media_type="text/csv")
    result = CsvDecoder().decode(request)
    assert result.status is DecodeStatus.SUCCEEDED
    return build_dataset_version(
        dataset_id=dataset_id,
        request=request,
        result=result,
        created_at=datetime(2026, 10, 2, 16, 0, tzinfo=UTC),
    )


def test_same_decoded_content_has_same_version_id_across_runs() -> None:
    first = _version(b"id,name\n1,Ada\n")
    second = _version(b"id,name\n1,Ada\n")

    assert first.ingestion_run_id != second.ingestion_run_id
    assert first.version_id == second.version_id
    assert first.reference.content_fingerprint == first.version_id


def test_changed_decoded_content_changes_version_id() -> None:
    first = _version(b"id,name\n1,Ada\n")
    second = _version(b"id,name\n1,Linus\n")

    assert first.version_id != second.version_id


def test_dataset_identity_is_dataset_and_version_pair() -> None:
    first = _version(b"id\n1\n", dataset_id="demo.one")
    second = _version(b"id\n1\n", dataset_id="demo.two")

    assert first.version_id == second.version_id
    assert first.reference.identity != second.reference.identity


def test_schema_fingerprint_and_raw_provenance_are_retained() -> None:
    version = _version(b"id,name\n1,Ada\n")

    assert version.reference.schema_fingerprint == version.schema.fingerprint
    assert version.source_artifact.kind == "raw"
    assert version.row_count == 1


def test_dataset_version_is_immutable() -> None:
    version = _version(b"id\n1\n")

    with pytest.raises(FrozenInstanceError):
        version.decoder_id = "other"  # type: ignore[misc]


def test_version_creation_rejects_request_result_identity_mismatch() -> None:
    first_request = _request(b"id\n1\n", media_type="text/csv")
    second_request = _request(b"id\n1\n", media_type="text/csv")
    result = CsvDecoder().decode(first_request)
    assert result.status is DecodeStatus.SUCCEEDED

    with pytest.raises(ValueError, match="ingestion_run_id mismatch"):
        build_dataset_version(
            dataset_id="demo.reference",
            request=second_request,
            result=result,
            created_at=datetime(2026, 10, 2, 16, 0, tzinfo=UTC),
        )
