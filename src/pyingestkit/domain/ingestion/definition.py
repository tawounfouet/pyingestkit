"""Immutable PyIngestKit V2 ingestion definition."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field

from pyingestkit.domain.artifacts import RawPolicy
from pyingestkit.domain.shared.validation import (
    require_non_blank,
    validate_metadata,
    validate_optional_text,
)
from pyingestkit.domain.sources import Source


@dataclass(frozen=True, slots=True)
class DefinitionFingerprint:
    """Deterministic fingerprint of runtime-independent ingestion intent."""

    algorithm: str
    value: str

    def __post_init__(self) -> None:
        require_non_blank(self.algorithm, "DefinitionFingerprint algorithm")
        require_non_blank(self.value, "DefinitionFingerprint value")

    def __str__(self) -> str:
        return f"{self.algorithm}:{self.value}"


@dataclass(frozen=True, slots=True)
class IngestionDefinition:
    """Canonical immutable V2 authoring root for one ingestion intent."""

    name: str
    source: Source
    decoder: str
    dataset: str
    raw_policy: RawPolicy = field(default_factory=RawPolicy)
    validation_policy: str | None = None
    versioning_policy: str | None = None
    publication_policy: str | None = None
    options: tuple[tuple[str, str], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.name, "IngestionDefinition name")
        if not isinstance(self.source, Source):
            raise TypeError("IngestionDefinition source must be a V2 Source.")
        require_non_blank(self.decoder, "IngestionDefinition decoder")
        require_non_blank(self.dataset, "IngestionDefinition dataset")
        if not isinstance(self.raw_policy, RawPolicy):
            raise TypeError("IngestionDefinition raw_policy must be a RawPolicy.")

        for name, value in (
            ("validation_policy", self.validation_policy),
            ("versioning_policy", self.versioning_policy),
            ("publication_policy", self.publication_policy),
        ):
            validate_optional_text(value, f"IngestionDefinition {name}")

        validate_metadata(self.options, name="IngestionDefinition options")
        validate_metadata(self.metadata, name="IngestionDefinition metadata")

    @property
    def fingerprint(self) -> DefinitionFingerprint:
        """Return a deterministic SHA-256 fingerprint of authored semantics."""
        payload = _normalize(
            {
                "name": self.name,
                "source": self.source.fingerprint_payload(),
                "decoder": self.decoder,
                "dataset": self.dataset,
                "raw_policy": self.raw_policy.fingerprint_payload(),
                "validation_policy": self.validation_policy,
                "versioning_policy": self.versioning_policy,
                "publication_policy": self.publication_policy,
                "options": sorted(self.options),
                "metadata": sorted(self.metadata),
            }
        )
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return DefinitionFingerprint(
            algorithm="sha256",
            value=hashlib.sha256(encoded).hexdigest(),
        )


def _normalize(value: object) -> object:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize(item) for key, item in value.items()
        }
    return value
