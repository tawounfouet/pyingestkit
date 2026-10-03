"""PyIngestKit 2.0 provider-neutral source and acquisition API."""

from pyingestkit.adapters.filesystem import FileAccessPolicy, FileSourceConnector
from pyingestkit.application.sources import SourceRegistry
from pyingestkit.domain.acquisition import (
    AcquisitionRequest,
    AcquisitionResult,
    AcquisitionStatus,
)
from pyingestkit.domain.sources import Source, SourceKind
from pyingestkit.ports.sources import (
    SourceConnector,
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)

__all__ = [
    "AcquisitionRequest",
    "AcquisitionResult",
    "AcquisitionStatus",
    "FileAccessPolicy",
    "FileSourceConnector",
    "Source",
    "SourceConnector",
    "SourceConnectorCapability",
    "SourceConnectorDescriptor",
    "SourceKind",
    "SourceRegistry",
]
