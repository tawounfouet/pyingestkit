from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from pyingestkit.domain.artifacts import ArtifactReference
from pyingestkit.domain.datasets import DatasetReference, DatasetVersionReference
from pyingestkit.domain.resources import CredentialReference, ResourceReference


def _resource() -> ResourceReference:
    return ResourceReference(
        namespace="pyingestkit.resource",
        resource_id="customers-source",
        locator="s3://data/customers.csv",
        media_type="text/csv",
    )


def test_resource_reference_is_portable_and_versioned() -> None:
    reference = _resource()

    assert reference.portable is True
    assert reference.CONTRACT_ID == "pykit.resource_reference"
    assert reference.contract_version == "1"


@pytest.mark.parametrize(
    "locator",
    [
        "https://user:password@example.test/data.csv",
        "https://example.test/data.csv?token=secret",
        "https://example.test/data.csv?x-amz-signature=abc",
    ],
)
def test_resource_reference_rejects_credential_bearing_locator(locator: str) -> None:
    with pytest.raises(ValueError):
        ResourceReference(
            namespace="pyingestkit.resource",
            resource_id="unsafe",
            locator=locator,
        )


@pytest.mark.parametrize("key", ["password", "api_key", "aws.secret"])
def test_resource_reference_rejects_credential_like_metadata(key: str) -> None:
    with pytest.raises(ValueError):
        ResourceReference(
            namespace="pyingestkit.resource",
            resource_id="unsafe-metadata",
            metadata=((key, "value"),),
        )


def test_artifact_reference_requires_checksum_pair() -> None:
    with pytest.raises(ValueError):
        ArtifactReference(
            artifact_id="raw-1",
            kind="raw",
            resource=_resource(),
            checksum="abc",
        )


def test_artifact_reference_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError):
        ArtifactReference(
            artifact_id="raw-1",
            kind="raw",
            resource=_resource(),
            created_at=datetime(2026, 10, 2),
        )


def test_artifact_reference_is_immutable() -> None:
    reference = ArtifactReference(
        artifact_id="raw-1",
        kind="raw",
        resource=_resource(),
        checksum="abc",
        checksum_algorithm="sha256",
        created_at=datetime(2026, 10, 2, tzinfo=UTC),
    )

    with pytest.raises(FrozenInstanceError):
        reference.kind = "manifest"  # type: ignore[misc]


def test_dataset_version_identity_is_dataset_and_version_pair() -> None:
    v1 = DatasetVersionReference(dataset_id="customers", version_id="v1")
    v2 = DatasetVersionReference(dataset_id="customers", version_id="v2")

    assert v1.identity == ("customers", "v1")
    assert v2.identity == ("customers", "v2")
    assert v1.identity != v2.identity


def test_dataset_reference_does_not_imply_immutable_version() -> None:
    reference = DatasetReference(dataset_id="customers", locator=_resource())

    assert not hasattr(reference, "version_id")


def test_dataset_version_reference_accepts_artifact_evidence() -> None:
    artifact = ArtifactReference(
        artifact_id="raw-1",
        kind="raw",
        resource=_resource(),
    )
    reference = DatasetVersionReference(
        dataset_id="customers",
        version_id="v1",
        artifact_reference=artifact,
    )

    assert reference.artifact_reference is artifact


def test_credential_reference_contains_identifiers_only() -> None:
    credential = CredentialReference(
        credential_id="vault://data-reader",
        provider="vault",
    )

    assert credential.portable is True
    assert not hasattr(credential, "password")
    assert not hasattr(credential, "secret")
    assert not hasattr(credential, "token")
