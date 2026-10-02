"""PyIngestKit V2 provider and persistence port contracts."""

from pyingestkit.ports.artifacts import ArtifactReader, ArtifactStore
from pyingestkit.ports.sources import (
    SourceConnector,
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)

__all__ = [
    "ArtifactReader",
    "ArtifactStore",
    "SourceConnector",
    "SourceConnectorCapability",
    "SourceConnectorDescriptor",
]
