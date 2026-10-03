"""PyIngestKit V2 dataset boundaries and immutable version semantics."""

from pyingestkit.domain.datasets.materialization import ResourceDatasetVersionRequestV2
from pyingestkit.domain.datasets.references import (
    DatasetReference,
    DatasetVersionReference,
)
from pyingestkit.domain.datasets.version import (
    DatasetVersion,
    build_dataset_version,
    dataset_content_fingerprint,
)

__all__ = [
    "DatasetReference",
    "ResourceDatasetVersionRequestV2",
    "DatasetVersion",
    "DatasetVersionReference",
    "build_dataset_version",
    "dataset_content_fingerprint",
]
