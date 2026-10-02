"""Portable credential references without secret material."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_contract_version,
    validate_optional_text,
)


@dataclass(frozen=True, slots=True)
class CredentialReference:
    """Reference to runtime-resolved credentials, never the credential value."""

    CONTRACT_ID: ClassVar[str] = "pykit.credential_reference"

    credential_id: str
    provider: str | None = None
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.credential_id, "credential_id")
        validate_optional_text(self.provider, "provider")
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True
