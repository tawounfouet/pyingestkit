"""Portable bounded-parser and encoding policies."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from enum import StrEnum

from pyingestkit.domain.shared.validation import require_non_blank


class EncodingErrorMode(StrEnum):
    """Allowed text-decoding error policy."""

    STRICT = "strict"


@dataclass(frozen=True, slots=True)
class EncodingPolicy:
    """Explicit text encoding policy for byte decoders."""

    encoding: str = "utf-8"
    errors: EncodingErrorMode = EncodingErrorMode.STRICT
    allow_utf8_bom: bool = True

    def __post_init__(self) -> None:
        require_non_blank(self.encoding, "EncodingPolicy encoding")
        try:
            codecs.lookup(self.encoding)
        except LookupError as exc:
            raise ValueError(f"Unknown text encoding: {self.encoding!r}") from exc
        if not isinstance(self.errors, EncodingErrorMode):
            raise TypeError("EncodingPolicy errors must be EncodingErrorMode.")
        if not isinstance(self.allow_utf8_bom, bool):
            raise TypeError("EncodingPolicy allow_utf8_bom must be bool.")


@dataclass(frozen=True, slots=True)
class DecoderLimits:
    """Provider-independent safety limits for foundation decoders."""

    max_bytes: int = 16 * 1024 * 1024
    max_rows: int = 1_000_000
    max_columns: int = 10_000
    max_field_chars: int = 1_000_000
    max_nesting_depth: int = 64
    max_keys_per_object: int = 10_000

    def __post_init__(self) -> None:
        for name in (
            "max_bytes",
            "max_rows",
            "max_columns",
            "max_field_chars",
            "max_nesting_depth",
            "max_keys_per_object",
        ):
            value = getattr(self, name)
            if not isinstance(value, int):
                raise TypeError(f"DecoderLimits {name} must be int.")
            if value <= 0:
                raise ValueError(f"DecoderLimits {name} must be positive.")
