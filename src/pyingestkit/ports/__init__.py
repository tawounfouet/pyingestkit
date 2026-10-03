"""Stable PyIngestKit 2.0 provider and persistence port contracts."""

from pyingestkit.ports.artifacts import ArtifactReader, ArtifactStore
from pyingestkit.ports.dataset_materialization import DatasetVersionMaterializerV2
from pyingestkit.ports.dataset_versions import DatasetPublisher, DatasetVersionStore
from pyingestkit.ports.decoders import Decoder, DecoderCapability, DecoderDescriptor
from pyingestkit.ports.sources import (
    SourceConnector,
    SourceConnectorCapability,
    SourceConnectorDescriptor,
)
from pyingestkit.ports.targets import DatasetTargetV2, TargetDescriptorV2

__all__ = [
    "ArtifactReader",
    "ArtifactStore",
    "DatasetPublisher",
    "DatasetTargetV2",
    "DatasetVersionMaterializerV2",
    "DatasetVersionStore",
    "Decoder",
    "DecoderCapability",
    "DecoderDescriptor",
    "SourceConnector",
    "SourceConnectorCapability",
    "SourceConnectorDescriptor",
    "TargetDescriptorV2",
]
