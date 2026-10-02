"""Explicit source connector registry."""

from __future__ import annotations

from collections.abc import Iterable

from pyingestkit.domain.sources import Source, SourceKind
from pyingestkit.ports.sources import SourceConnector, SourceConnectorDescriptor


class SourceRegistry:
    """Explicit connector registry with no import-time global mutation."""

    def __init__(self) -> None:
        self._connectors: dict[str, SourceConnector] = {}

    def register(
        self,
        connector: SourceConnector,
        *,
        replace: bool = False,
    ) -> None:
        descriptor = connector.descriptor
        if not isinstance(descriptor, SourceConnectorDescriptor):
            raise TypeError(
                "Source connector descriptor must be a SourceConnectorDescriptor."
            )
        if descriptor.id in self._connectors and not replace:
            raise ValueError(
                f"Source connector already registered: {descriptor.id}"
            )
        self._connectors[descriptor.id] = connector

    def register_many(
        self,
        connectors: Iterable[SourceConnector],
        *,
        replace: bool = False,
    ) -> None:
        for connector in connectors:
            self.register(connector, replace=replace)

    def get(self, connector_id: str) -> SourceConnector:
        try:
            return self._connectors[connector_id]
        except KeyError as exc:
            raise KeyError(
                f"Unknown source connector: {connector_id}"
            ) from exc

    def resolve(self, source: Source) -> SourceConnector:
        if not isinstance(source, Source):
            raise TypeError("SourceRegistry.resolve expects a V2 Source.")

        if source.kind is SourceKind.CUSTOM:
            if source.connector_id is None:
                raise ValueError("Custom Source requires connector_id.")
            connector = self.get(source.connector_id)
            if source.kind not in connector.descriptor.supported_source_kinds:
                raise ValueError(
                    f"Source connector {source.connector_id!r} does not support "
                    f"source kind {source.kind.value!r}."
                )
            return connector

        matches = tuple(
            connector
            for connector in self._connectors.values()
            if source.kind in connector.descriptor.supported_source_kinds
        )
        if not matches:
            raise KeyError(
                f"No source connector registered for kind: {source.kind.value}"
            )
        if len(matches) > 1:
            ids = sorted(connector.descriptor.id for connector in matches)
            raise LookupError(
                f"Multiple source connectors registered for "
                f"{source.kind.value!r}: {ids}"
            )
        return matches[0]

    def list(self) -> tuple[SourceConnector, ...]:
        return tuple(
            self._connectors[key] for key in sorted(self._connectors)
        )

    def __len__(self) -> int:
        return len(self._connectors)
