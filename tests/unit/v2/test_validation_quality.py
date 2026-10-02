from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pyingestkit.quality import QualityEvidence
from pyingestkit.validation import (
    MinimumRowsV2,
    RequiredFieldV2,
    UniqueFieldV2,
    ValidationLimits,
    ValidationRequest,
    ValidationSeverity,
    validate_v2,
)

from .test_decoders import _request
from pyingestkit.decoders import CsvDecoder, DecodeStatus


def _validation_request(content: bytes, *, max_issues: int = 1000) -> ValidationRequest:
    decode_request = _request(content, media_type="text/csv")
    decoded = CsvDecoder().decode(decode_request)
    assert decoded.status is DecodeStatus.SUCCEEDED
    assert decoded.representation is not None
    return ValidationRequest(
        ingestion_run_id=decode_request.ingestion_run_id,
        correlation=decode_request.correlation,
        artifact=decode_request.artifact,
        decoder_id=decoded.decoder_id,
        representation=decoded.representation,
        limits=ValidationLimits(max_issues=max_issues),
    )


def test_foundation_rules_validate_decoded_representation() -> None:
    request = _validation_request(b"id,name\n1,Ada\n1,\n")
    result = validate_v2(
        request,
        (MinimumRowsV2(2), RequiredFieldV2("name"), UniqueFieldV2("id")),
    )

    assert result.is_valid is False
    assert result.error_count == 2
    assert [issue.rule for issue in result.issues] == ["required_field", "unique_field"]
    assert [issue.row_index for issue in result.issues] == [1, 1]


def test_validation_is_deterministic_and_non_mutating() -> None:
    request = _validation_request(b"id,name\n1,Ada\n1,Linus\n")
    before = request.representation

    first = validate_v2(request, (UniqueFieldV2("id"),))
    second = validate_v2(request, (UniqueFieldV2("id"),))

    assert first == second
    assert request.representation == before


def test_issue_collection_is_bounded_and_explicitly_truncated() -> None:
    request = _validation_request(b"id,name\n1,\n2,\n3,\n", max_issues=2)
    result = validate_v2(request, (RequiredFieldV2("name"),))

    assert result.issue_count == 2
    assert result.issues_truncated is True


def test_warning_does_not_make_result_invalid() -> None:
    request = _validation_request(b"id\n1\n")
    result = validate_v2(
        request,
        (MinimumRowsV2(2, severity=ValidationSeverity.WARNING),),
    )

    assert result.is_valid is True
    assert result.warning_count == 1


def test_quality_evidence_binds_validation_to_provenance() -> None:
    request = _validation_request(b"id\n1\n")
    result = validate_v2(request, (MinimumRowsV2(1),))
    evidence = QualityEvidence(
        ingestion_run_id=request.ingestion_run_id,
        correlation=request.correlation,
        source_artifact=request.artifact,
        decoder_id=request.decoder_id,
        validation=result,
    )

    assert evidence.validation.is_valid is True
    assert evidence.source_artifact == request.artifact

    with pytest.raises(FrozenInstanceError):
        evidence.decoder_id = "other"  # type: ignore[misc]
