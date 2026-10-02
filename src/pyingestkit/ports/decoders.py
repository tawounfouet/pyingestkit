"""Decoder extension port contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pyingestkit.domain.decoding.models import DecodeRequest, DecodeResult
from pyingestkit.domain.shared.validation import require_non_blank


class DecoderCapability(StrEnum):
    """Capabilities a decoder may explicitly advertise."""

    ROW_COUNT = "row_count"
    SCHEMA_EVIDENCE = "schema_evidence"
    NESTED_VALUES = "nested_values"


@dataclass(frozen=True, slots=True)
class DecoderDescriptor:
    """Portable description of one decoder implementation."""

    id: str
    display_name: str
    decoder_version: str
    media_types: tuple[str, ...]
    formats: tuple[str, ...]
    capabilities: tuple[DecoderCapability, ...]
    configuration_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_non_blank(self.id, "DecoderDescriptor id")
        require_non_blank(self.display_name, "DecoderDescriptor display_name")
        require_non_blank(self.decoder_version, "DecoderDescriptor decoder_version")
        _validate_text_values(self.media_types, "DecoderDescriptor media_types")
        _validate_text_values(self.formats, "DecoderDescriptor formats")
        _validate_text_values(
            self.configuration_fields,
            "DecoderDescriptor configuration_fields",
            allow_empty=True,
        )
        if not isinstance(self.capabilities, tuple):
            raise TypeError("DecoderDescriptor capabilities must be a tuple.")
        if any(not isinstance(value, DecoderCapability) for value in self.capabilities):
            raise TypeError("DecoderDescriptor capabilities must contain DecoderCapability values.")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("DecoderDescriptor capabilities must be unique.")
        required = {DecoderCapability.ROW_COUNT, DecoderCapability.SCHEMA_EVIDENCE}
        if not required.issubset(self.capabilities):
            raise ValueError("DecoderDescriptor must advertise row-count and schema evidence.")


@runtime_checkable
class Decoder(Protocol):
    """Decode bytes into ingestion representation without business transformation."""

    @property
    def descriptor(self) -> DecoderDescriptor: ...

    def decode(self, request: DecodeRequest) -> DecodeResult: ...


def _validate_text_values(
    values: tuple[str, ...],
    name: str,
    *,
    allow_empty: bool = False,
) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple.")
    if not values and not allow_empty:
        raise ValueError(f"{name} must not be empty.")
    for value in values:
        require_non_blank(value, f"{name} item")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must contain unique values.")
