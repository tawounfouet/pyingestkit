"""Filesystem adapters for the PyIngestKit V2 local reference profile."""

from pyingestkit.adapters.filesystem.artifact_store import (
    FileArtifactReader,
    FileArtifactStore,
)
from pyingestkit.adapters.filesystem.conditional_publisher import (
    FileConditionalDatasetPublisher,
)
from pyingestkit.adapters.filesystem.dataset_version_materializer import (
    FileCsvDatasetVersionMaterializerV2,
)
from pyingestkit.adapters.filesystem.dataset_version_store import FileDatasetVersionStore
from pyingestkit.adapters.filesystem.garbage_collector import (
    FileDatasetVersionGarbageCollector,
)
from pyingestkit.adapters.filesystem.source import (
    FileAccessPolicy,
    FileSourceConnector,
)

__all__ = [
    "FileAccessPolicy",
    "FileArtifactReader",
    "FileArtifactStore",
    "FileConditionalDatasetPublisher",
    "FileCsvDatasetVersionMaterializerV2",
    "FileDatasetVersionGarbageCollector",
    "FileDatasetVersionStore",
    "FileSourceConnector",
]
