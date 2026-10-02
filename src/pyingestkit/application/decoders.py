"""Explicit decoder registry with no import-time activation."""

from __future__ import annotations

from collections.abc import Iterable

from pyingestkit.ports.decoders import Decoder, DecoderDescriptor


class DecoderRegistry:
    """Instance-owned registry for stable decoder IDs."""

    def __init__(self) -> None:
        self._decoders: dict[str, Decoder] = {}

    def register(self, decoder: Decoder, *, replace: bool = False) -> None:
        descriptor = decoder.descriptor
        if not isinstance(descriptor, DecoderDescriptor):
            raise TypeError("Decoder descriptor must be a DecoderDescriptor.")
        if descriptor.id in self._decoders and not replace:
            raise ValueError(f"Decoder already registered: {descriptor.id}")
        self._decoders[descriptor.id] = decoder

    def register_many(
        self,
        decoders: Iterable[Decoder],
        *,
        replace: bool = False,
    ) -> None:
        for decoder in decoders:
            self.register(decoder, replace=replace)

    def get(self, decoder_id: str) -> Decoder:
        try:
            return self._decoders[decoder_id]
        except KeyError as exc:
            raise KeyError(f"Unknown decoder: {decoder_id}") from exc

    def list(self) -> tuple[Decoder, ...]:
        return tuple(self._decoders[key] for key in sorted(self._decoders))

    def __len__(self) -> int:
        return len(self._decoders)
