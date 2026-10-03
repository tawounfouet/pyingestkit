from __future__ import annotations

import pytest

from pyingestkit.datasets import DatasetVersionReference, dataset_content_fingerprint
from pyingestkit.domain.decoding import DecodedRecord, DecodedRepresentation
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import IngestionRunId
from pyingestkit.domain.targets import TargetLoadModeV2, TargetLoadRequestV2


def _representation() -> DecodedRepresentation:
    return DecodedRepresentation(
        records=(
            DecodedRecord(fields=(("id", "1"), ("name", "Ada"))),
            DecodedRecord(fields=(("id", "2"), ("name", "Linus"))),
        )
    )


def _request(
    representation: DecodedRepresentation | None = None,
    *,
    columns: tuple[str, ...] = (),
) -> TargetLoadRequestV2:
    value = _representation() if representation is None else representation
    run_id = IngestionRunId.new()
    return TargetLoadRequestV2(
        target_id="postgres.demo",
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        dataset_version=DatasetVersionReference(
            dataset_id="demo.people",
            version_id=dataset_content_fingerprint(value),
        ),
        representation=value,
        table="people",
        columns=columns,
    )


def test_target_request_binds_exact_dataset_version_content() -> None:
    representation = _representation()
    wrong = DatasetVersionReference(
        dataset_id="demo.people",
        version_id="sha256-" + "f" * 64,
    )
    run_id = IngestionRunId.new()

    with pytest.raises(ValueError, match="does not match dataset version identity"):
        TargetLoadRequestV2(
            target_id="postgres.demo",
            ingestion_run_id=run_id,
            correlation=CorrelationContext(ingestion_run_id=str(run_id)),
            dataset_version=wrong,
            representation=representation,
            table="people",
        )


def test_target_request_derives_stable_union_column_order() -> None:
    representation = DecodedRepresentation(
        records=(
            DecodedRecord(fields=(("id", "1"), ("name", "Ada"))),
            DecodedRecord(fields=(("id", "2"), ("email", "a@example.test"))),
        )
    )

    request = _request(representation)

    assert request.resolved_columns == ("id", "name", "email")


def test_explicit_columns_must_cover_all_decoded_fields() -> None:
    with pytest.raises(ValueError, match="must match decoded representation fields"):
        _request(columns=("id",))


def test_empty_representation_requires_explicit_columns() -> None:
    empty = DecodedRepresentation(records=())

    with pytest.raises(ValueError, match="requires explicit columns"):
        _request(empty)

    request = _request(empty, columns=("id", "name"))
    assert request.resolved_columns == ("id", "name")
    assert request.mode is TargetLoadModeV2.APPEND
