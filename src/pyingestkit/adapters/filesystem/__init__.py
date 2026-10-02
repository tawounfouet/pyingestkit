"""Filesystem adapters for the PyIngestKit V2 local reference profile."""

from pyingestkit.adapters.filesystem.artifact_store import (
    FileArtifactReader,
    FileArtifactStore,
)
from pyingestkit.adapters.filesystem.source import (
    FileAccessPolicy,
    FileSourceConnector,
)

__all__ = [
    "FileAccessPolicy",
    "FileArtifactReader",
    "FileArtifactStore",
    "FileSourceConnector",
]
