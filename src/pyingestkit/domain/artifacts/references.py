"""Portable references to durable PyIngestKit artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

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
class ArtifactReference:
    """Portable reference to durable evidence such as RAW or reports."""

    CONTRACT_ID: ClassVar[str] = "pykit.artifact_reference"

    artifact_id: str
    kind: str
    resource: ResourceReference
    checksum: str | None = None
    checksum_algorithm: str | None = None
    media_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    owner: str = "pyingestkit"
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.artifact_id, "ArtifactReference artifact_id")
        require_non_blank(self.kind, "ArtifactReference kind")
        if not isinstance(self.resource, ResourceReference):
            raise TypeError("ArtifactReference resource must be a ResourceReference.")

        validate_optional_text(self.checksum, "ArtifactReference checksum")
        validate_optional_text(
            self.checksum_algorithm,
            "ArtifactReference checksum_algorithm",
        )
        if (self.checksum is None) != (self.checksum_algorithm is None):
            raise ValueError(
                "ArtifactReference checksum and checksum_algorithm must be provided together."
            )

        validate_optional_text(self.media_type, "ArtifactReference media_type")
        if self.size_bytes is not None:
            if not isinstance(self.size_bytes, int):
                raise TypeError("ArtifactReference size_bytes must be an int.")
            if self.size_bytes < 0:
                raise ValueError("ArtifactReference size_bytes must be non-negative.")

        validate_aware_datetime(self.created_at, "ArtifactReference created_at")
        validate_metadata(self.metadata, name="ArtifactReference metadata")
        validate_owner(self.owner)
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True
