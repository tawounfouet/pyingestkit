"""RAW retention intent for PyIngestKit V2 definitions."""

from __future__ import annotations

from dataclasses import dataclass

from pyingestkit.domain.shared.validation import validate_optional_text


@dataclass(frozen=True, slots=True)
class RawPolicy:
    """Runtime-independent policy describing whether RAW evidence is retained."""

    enabled: bool = True
    retain: bool = True
    checksum: str | None = "sha256"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("RawPolicy enabled must be bool.")
        if not isinstance(self.retain, bool):
            raise TypeError("RawPolicy retain must be bool.")
        validate_optional_text(self.checksum, "RawPolicy checksum")
        if not self.enabled and self.retain:
            raise ValueError("RawPolicy cannot retain RAW when RAW capture is disabled.")

    def fingerprint_payload(self) -> dict[str, object]:
        """Return semantic material for IngestionDefinition fingerprinting."""
        return {
            "enabled": self.enabled,
            "retain": self.retain,
            "checksum": self.checksum,
        }
