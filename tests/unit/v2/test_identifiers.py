from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pyingestkit.domain.shared import CorrelationId, IngestionRunId


def test_ingestion_run_id_round_trips_through_string_parsing() -> None:
    run_id = IngestionRunId.new()

    assert IngestionRunId.parse(str(run_id)) == run_id
    assert str(run_id.value) == str(run_id)


def test_ingestion_identity_is_distinct_from_correlation_identity() -> None:
    run_id = IngestionRunId.new()
    correlation_id = CorrelationId(run_id.value)

    assert run_id != correlation_id


def test_identifiers_are_immutable() -> None:
    run_id = IngestionRunId.new()

    with pytest.raises(FrozenInstanceError):
        run_id.value = run_id.value  # type: ignore[misc]


@pytest.mark.parametrize("value", ["", "   "])
def test_identifier_parse_rejects_blank_text(value: str) -> None:
    with pytest.raises(ValueError):
        IngestionRunId.parse(value)
