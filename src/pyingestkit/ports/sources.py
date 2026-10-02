"""Source connector port contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pyingestkit.domain.acquisition import AcquisitionRequest, AcquisitionResult
from pyingestkit.domain.shared.validation import require_non_blank
from pyingestkit.domain.sources import SourceKind


class SourceConnectorCapability(StrEnum):
    """Capabilities that a source connector may explicitly advertise."""

    ACQUIRE = "acquire"
    RECONCILE = "reconcile"


@dataclass(frozen=True, slots=True)
class SourceConnectorDescriptor:
    """Portable descriptor for one source connector implementation."""

    id: str
    display_name: str
    connector_version: str
    supported_source_kinds: tuple[SourceKind, ...]
    capabilities: tuple[SourceConnectorCapability, ...] = (SourceConnectorCapability.ACQUIRE,)
    optional_dependencies_available: bool = True

    def __post_init__(self) -> None:
        require_non_blank(self.id, "SourceConnectorDescriptor id")
        require_non_blank(
            self.display_name,
            "SourceConnectorDescriptor display_name",
        )
        require_non_blank(
            self.connector_version,
            "SourceConnectorDescriptor connector_version",
        )
        if not isinstance(self.supported_source_kinds, tuple):
            raise TypeError("SourceConnectorDescriptor supported_source_kinds must be a tuple.")
        if not self.supported_source_kinds:
            raise ValueError("SourceConnectorDescriptor requires at least one source kind.")
        if any(not isinstance(kind, SourceKind) for kind in self.supported_source_kinds):
            raise TypeError("SourceConnectorDescriptor source kinds must be SourceKind values.")
        if len(set(self.supported_source_kinds)) != len(self.supported_source_kinds):
            raise ValueError("SourceConnectorDescriptor source kinds must be unique.")

        if not isinstance(self.capabilities, tuple):
            raise TypeError("SourceConnectorDescriptor capabilities must be a tuple.")
        if any(
            not isinstance(capability, SourceConnectorCapability)
            for capability in self.capabilities
        ):
            raise TypeError(
                "SourceConnectorDescriptor capabilities must contain "
                "SourceConnectorCapability values."
            )
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("SourceConnectorDescriptor capabilities must be unique.")
        if SourceConnectorCapability.ACQUIRE not in self.capabilities:
            raise ValueError("SourceConnectorDescriptor must advertise ACQUIRE.")
        if not isinstance(self.optional_dependencies_available, bool):
            raise TypeError(
                "SourceConnectorDescriptor optional_dependencies_available must be bool."
            )


@runtime_checkable
class SourceConnector(Protocol):
    """Port implemented by ingestion source adapters."""

    @property
    def descriptor(self) -> SourceConnectorDescriptor: ...

    def acquire(self, request: AcquisitionRequest) -> AcquisitionResult: ...
