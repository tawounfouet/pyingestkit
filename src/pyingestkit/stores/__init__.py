"""PyIngestKit V2 durable-store API during the V1 transition."""

from pyingestkit.adapters.filesystem import FileArtifactReader, FileArtifactStore
from pyingestkit.ports.artifacts import ArtifactReader, ArtifactStore

__all__ = [
    "ArtifactReader",
    "ArtifactStore",
    "FileArtifactReader",
    "FileArtifactStore",
]
