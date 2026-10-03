"""PyIngestKit 2.0 public API."""

import logging as _stdlib_logging

from ._version import __version__ as __version__
from .application.runtime import IngestionRuntime
from .domain.artifacts.references import ArtifactReference
from .domain.datasets.publication import PublishedDataset
from .domain.datasets.references import DatasetVersionReference
from .domain.datasets.version import DatasetVersion
from .domain.ingestion import IngestionDefinition
from .domain.resources import ResourceReference
from .domain.runtime.execution import IngestionResult, IngestionRun
from .domain.shared.identifiers import IngestionRunId
from .domain.sources import Source

__all__ = [
    "ArtifactReference",
    "DatasetVersion",
    "DatasetVersionReference",
    "IngestionDefinition",
    "IngestionResult",
    "IngestionRun",
    "IngestionRunId",
    "IngestionRuntime",
    "PublishedDataset",
    "ResourceReference",
    "Source",
]

# Library best practice: never configure application handlers at import time.
_stdlib_logging.getLogger(__name__).addHandler(_stdlib_logging.NullHandler())
