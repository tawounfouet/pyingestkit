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


def test_upsert_and_merge_modes_require_key_columns() -> None:
    representation = _representation()
    run_id = IngestionRunId.new()

    for mode in (TargetLoadModeV2.UPSERT, TargetLoadModeV2.MERGE):
        with pytest.raises(ValueError, match=f"requires key_columns for {mode.value} mode"):
            TargetLoadRequestV2(
                target_id="postgres.demo",
                ingestion_run_id=run_id,
                correlation=CorrelationContext(ingestion_run_id=str(run_id)),
                dataset_version=DatasetVersionReference(
                    dataset_id="demo.people",
                    version_id=dataset_content_fingerprint(representation),
                ),
                representation=representation,
                table="people",
                mode=mode,
            )


def test_key_columns_must_be_in_resolved_columns() -> None:
    representation = _representation()
    run_id = IngestionRunId.new()

    with pytest.raises(ValueError, match="key_column 'missing' must be in resolved columns"):
        TargetLoadRequestV2(
            target_id="postgres.demo",
            ingestion_run_id=run_id,
            correlation=CorrelationContext(ingestion_run_id=str(run_id)),
            dataset_version=DatasetVersionReference(
                dataset_id="demo.people",
                version_id=dataset_content_fingerprint(representation),
            ),
            representation=representation,
            table="people",
            mode=TargetLoadModeV2.UPSERT,
            key_columns=("missing",),
        )


def test_update_columns_validation_and_effective_calculation() -> None:
    representation = DecodedRepresentation(
        records=(DecodedRecord(fields=(("id", "1"), ("name", "Ada"), ("age", "36"))),)
    )
    run_id = IngestionRunId.new()

    # Overlap with key_columns is rejected
    with pytest.raises(ValueError, match="cannot overlap with key_columns"):
        TargetLoadRequestV2(
            target_id="postgres.demo",
            ingestion_run_id=run_id,
            correlation=CorrelationContext(ingestion_run_id=str(run_id)),
            dataset_version=DatasetVersionReference(
                dataset_id="demo.people",
                version_id=dataset_content_fingerprint(representation),
            ),
            representation=representation,
            table="people",
            mode=TargetLoadModeV2.UPSERT,
            key_columns=("id",),
            update_columns=("id", "name"),
        )

    # Valid explicit update_columns
    request_explicit = TargetLoadRequestV2(
        target_id="postgres.demo",
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        dataset_version=DatasetVersionReference(
            dataset_id="demo.people",
            version_id=dataset_content_fingerprint(representation),
        ),
        representation=representation,
        table="people",
        mode=TargetLoadModeV2.UPSERT,
        key_columns=("id",),
        update_columns=("name",),
        idempotent=True,
    )
    assert request_explicit.effective_update_columns == ("name",)
    assert request_explicit.idempotent is True

    # Automatic fallback: effective_update_columns = resolved_columns minus key_columns
    request_default = TargetLoadRequestV2(
        target_id="postgres.demo",
        ingestion_run_id=run_id,
        correlation=CorrelationContext(ingestion_run_id=str(run_id)),
        dataset_version=DatasetVersionReference(
            dataset_id="demo.people",
            version_id=dataset_content_fingerprint(representation),
        ),
        representation=representation,
        table="people",
        mode=TargetLoadModeV2.UPSERT,
        key_columns=("id",),
    )
    assert request_default.effective_update_columns == ("name", "age")
