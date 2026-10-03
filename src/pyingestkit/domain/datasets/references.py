"""Portable dataset and dataset-version references."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from pyingestkit.domain.artifacts.references import ArtifactReference
from pyingestkit.domain.resources import ResourceReference
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_aware_datetime,
    validate_contract_version,
    validate_metadata,
    validate_optional_text,
    validate_owner,
)


@dataclass(frozen=True, slots=True)
class DatasetReference:
    """Reference to a logical governed dataset identity."""

    CONTRACT_ID: ClassVar[str] = "pykit.dataset_reference"

    dataset_id: str
    schema_fingerprint: str | None = None
    locator: ResourceReference | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    owner: str = "pyingestkit"
    namespace: str = "pyingestkit.dataset"
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.dataset_id, "DatasetReference dataset_id")
        validate_optional_text(
            self.schema_fingerprint,
            "DatasetReference schema_fingerprint",
        )
        if self.locator is not None and not isinstance(self.locator, ResourceReference):
            raise TypeError("DatasetReference locator must be a ResourceReference.")
        validate_metadata(self.metadata, name="DatasetReference metadata")
        validate_owner(self.owner)
        require_non_blank(self.namespace, "DatasetReference namespace")
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class DatasetVersionReference:
    """Reference to one immutable durable version of a dataset."""

    CONTRACT_ID: ClassVar[str] = "pykit.dataset_version_reference"

    dataset_id: str
    version_id: str
    created_at: datetime | None = None
    schema_fingerprint: str | None = None
    content_fingerprint: str | None = None
    artifact_reference: ArtifactReference | None = None
    locator: ResourceReference | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    owner: str = "pyingestkit"
    namespace: str = "pyingestkit.dataset_version"
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.dataset_id, "DatasetVersionReference dataset_id")
        require_non_blank(self.version_id, "DatasetVersionReference version_id")
        validate_aware_datetime(self.created_at, "DatasetVersionReference created_at")
        validate_optional_text(
            self.schema_fingerprint,
            "DatasetVersionReference schema_fingerprint",
        )
        validate_optional_text(
            self.content_fingerprint,
            "DatasetVersionReference content_fingerprint",
        )
        if self.artifact_reference is not None and not isinstance(
            self.artifact_reference,
            ArtifactReference,
        ):
            raise TypeError(
                "DatasetVersionReference artifact_reference must be an ArtifactReference."
            )
        if self.locator is not None and not isinstance(self.locator, ResourceReference):
            raise TypeError("DatasetVersionReference locator must be a ResourceReference.")
        validate_metadata(self.metadata, name="DatasetVersionReference metadata")
        validate_owner(self.owner)
        require_non_blank(self.namespace, "DatasetVersionReference namespace")
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True

    @property
    def identity(self) -> tuple[str, str]:
        """Return the immutable dataset/version identity pair."""
        return (self.dataset_id, self.version_id)
