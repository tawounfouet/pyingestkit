from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from pyingestkit.domain.artifacts import RawPolicy
from pyingestkit.domain.ingestion import IngestionDefinition
from pyingestkit.domain.resources import CredentialReference, ResourceReference
from pyingestkit.domain.sources import Source, SourceKind


def test_source_factories_are_declarative_values() -> None:
    file_source = Source.file(path="/data/customers.csv")
    http_source = Source.http(url="https://example.test/customers.csv")
    object_source = Source.object(uri="s3://bucket/customers.csv")
    database_source = Source.database(
        connection="analytics",
        query="select * from customers",
    )

    assert file_source.kind is SourceKind.FILE
    assert http_source.kind is SourceKind.HTTP
    assert object_source.kind is SourceKind.OBJECT
    assert database_source.kind is SourceKind.DATABASE


def test_source_can_reference_but_not_resolve_credentials() -> None:
    credential = CredentialReference(credential_id="vault://data-reader")
    source = Source.http(
        url="https://example.test/customers.csv",
        credential=credential,
    )

    assert source.credential is credential
    assert not hasattr(source, "password")
    assert not hasattr(source, "secret")
    assert not hasattr(source, "client")


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.test/customers.csv",
        "https://user:password@example.test/customers.csv",
        "https://example.test/customers.csv?token=secret",
    ],
)
def test_http_source_rejects_non_http_or_credential_bearing_urls(url: str) -> None:
    with pytest.raises(ValueError):
        Source.http(url=url)


def test_database_source_requires_logical_connection_not_dsn() -> None:
    with pytest.raises(ValueError):
        Source.database(
            connection="postgresql://user:secret@db/app",
            query="select 1",
        )


def test_source_custom_requires_explicit_connector() -> None:
    source = Source.custom(
        connector_id="vendor.export",
        options=(("mode", "snapshot"),),
    )

    assert source.kind is SourceKind.CUSTOM
    assert source.connector_id == "vendor.export"


def test_source_is_not_resource_reference() -> None:
    source = Source.object(uri="s3://bucket/customers.csv")

    assert not isinstance(source, ResourceReference)


def test_ingestion_definition_is_immutable_and_has_no_runtime_state() -> None:
    definition = IngestionDefinition(
        name="customers_ingestion",
        source=Source.file(path="/data/customers.csv"),
        decoder="csv",
        dataset="customers",
    )

    with pytest.raises(FrozenInstanceError):
        definition.name = "changed"  # type: ignore[misc]

    names = {field.name for field in fields(IngestionDefinition)}
    assert names.isdisjoint(
        {
            "ingestion_run_id",
            "retry_count",
            "status",
            "task_attempt",
            "provider_client",
        }
    )


def test_ingestion_definition_owns_runtime_independent_policy_hooks() -> None:
    definition = IngestionDefinition(
        name="customers_ingestion",
        source=Source.file(path="/data/customers.csv"),
        decoder="csv",
        dataset="customers",
        raw_policy=RawPolicy(enabled=True, retain=True, checksum="sha256"),
        validation_policy="strict-v1",
        versioning_policy="content-addressed-v1",
        publication_policy="publish-current-v1",
        options=(("encoding", "utf-8"),),
    )

    assert definition.raw_policy.retain is True
    assert definition.validation_policy == "strict-v1"
    assert definition.versioning_policy == "content-addressed-v1"
    assert definition.publication_policy == "publish-current-v1"


def test_definition_fingerprint_is_deterministic_and_order_normalized() -> None:
    first = IngestionDefinition(
        name="customers_ingestion",
        source=Source.file(
            path="/data/customers.csv",
            metadata=(("owner", "crm"), ("zone", "landing")),
        ),
        decoder="csv",
        dataset="customers",
        metadata=(("b", "2"), ("a", "1")),
    )
    second = IngestionDefinition(
        name="customers_ingestion",
        source=Source.file(
            path="/data/customers.csv",
            metadata=(("zone", "landing"), ("owner", "crm")),
        ),
        decoder="csv",
        dataset="customers",
        metadata=(("a", "1"), ("b", "2")),
    )

    assert first.fingerprint == second.fingerprint
    assert first.fingerprint.algorithm == "sha256"
    assert len(first.fingerprint.value) == 64


def test_definition_fingerprint_changes_with_semantics() -> None:
    first = IngestionDefinition(
        name="customers_ingestion",
        source=Source.file(path="/data/customers.csv"),
        decoder="csv",
        dataset="customers",
    )
    second = IngestionDefinition(
        name="customers_ingestion",
        source=Source.file(path="/data/customers.csv"),
        decoder="json",
        dataset="customers",
    )

    assert first.fingerprint != second.fingerprint


def test_definition_rejects_nonportable_metadata() -> None:
    with pytest.raises(ValueError):
        IngestionDefinition(
            name="customers_ingestion",
            source=Source.file(path="/data/customers.csv"),
            decoder="csv",
            dataset="customers",
            metadata=(("api_token", "secret"),),
        )


def test_raw_policy_disallows_retain_when_capture_disabled() -> None:
    with pytest.raises(ValueError):
        RawPolicy(enabled=False, retain=True)
