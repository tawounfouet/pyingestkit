"""Portable idempotency references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_contract_version,
    validate_owner,
)


@dataclass(frozen=True, slots=True)
class IdempotencyReference:
    """Scoped idempotency identity for one ingestion-owned operation."""

    CONTRACT_ID: ClassVar[str] = "pykit.idempotency_reference"

    namespace: str
    key: str
    scope: str
    owner: str = "pyingestkit"
    contract_version: str = "1"

    def __post_init__(self) -> None:
        require_non_blank(self.namespace, "IdempotencyReference namespace")
        require_non_blank(self.key, "IdempotencyReference key")
        require_non_blank(self.scope, "IdempotencyReference scope")
        validate_owner(self.owner)
        validate_contract_version(self.contract_version)

    @property
    def portable(self) -> bool:
        return True
