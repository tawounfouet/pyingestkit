from __future__ import annotations

from dataclasses import fields

from pyingestkit.domain.resources import CredentialReference
from pyingestkit.domain.runtime import CorrelationContext
from pyingestkit.domain.shared import CorrelationId, IngestionRunId


def test_credential_reference_has_no_raw_secret_field() -> None:
    field_names = {field.name.lower() for field in fields(CredentialReference)}

    assert field_names.isdisjoint(
        {
            "access_key",
            "api_key",
            "password",
            "private_key",
            "secret",
            "token",
        }
    )


def test_native_run_id_is_not_correlation_id() -> None:
    assert IngestionRunId is not CorrelationId
    assert not issubclass(IngestionRunId, CorrelationId)
    assert not issubclass(CorrelationId, IngestionRunId)


def test_correlation_context_keeps_native_ids_as_external_text() -> None:
    field_types = {field.name: str(field.type) for field in fields(CorrelationContext)}

    assert "CorrelationId" in field_types["correlation_id"]
    assert "str" in field_types["ingestion_run_id"]
