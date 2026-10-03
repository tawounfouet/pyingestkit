"""Portable V2 dataset references and immutable logical versions.

The V1 versioning package remains unchanged during the V2 transition.
"""

from pyingestkit.domain.datasets import (
    DatasetReference,
    DatasetVersion,
    DatasetVersionReference,
    ResourceDatasetVersionRequestV2,
    build_dataset_version,
    dataset_content_fingerprint,
)
from pyingestkit.domain.datasets.publication import PublishedDataset

__all__ = [
    "DatasetReference",
    "DatasetVersion",
    "DatasetVersionReference",
    "PublishedDataset",
    "ResourceDatasetVersionRequestV2",
    "build_dataset_version",
    "dataset_content_fingerprint",
]
