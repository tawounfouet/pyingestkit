"""Portable physical-resource references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_contract_version,
    validate_credential_safe_locator,
    validate_metadata,
    validate_optional_text,
)


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """Portable identity/location contract for one physical resource."""

    CONTRACT_ID: ClassVar[str] = "pykit.resource_reference"

    namespace: str
    resource_id: str
    locator: str | None = None
    media_type: str | None = None
    format: str | None = None
    schema_fingerprint: str | None = None
    metadata: tuple[tuple[str, str], ...] = ()
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.namespace, "ResourceReference namespace")
        require_non_blank(self.resource_id, "ResourceReference resource_id")
        validate_credential_safe_locator(self.locator, "ResourceReference locator")
        validate_optional_text(self.media_type, "ResourceReference media_type")
        validate_optional_text(self.format, "ResourceReference format")
        validate_optional_text(
            self.schema_fingerprint,
            "ResourceReference schema_fingerprint",
        )
        validate_metadata(self.metadata, name="ResourceReference metadata")
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True
