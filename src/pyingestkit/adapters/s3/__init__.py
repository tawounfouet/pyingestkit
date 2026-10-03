"""S3-compatible adapters for PyIngestKit V2."""

from pyingestkit.adapters.s3._objects import (
    S3ClientV2,
    S3ConditionalWriteCapabilityErrorV2,
)
from pyingestkit.adapters.s3.artifact_store import S3ArtifactReaderV2, S3ArtifactStoreV2
from pyingestkit.adapters.s3.conditional_publisher import S3ConditionalDatasetPublisher
from pyingestkit.adapters.s3.dataset_version_store import S3DatasetVersionStoreV2

__all__ = [
    "S3ArtifactReaderV2",
    "S3ArtifactStoreV2",
    "S3ClientV2",
    "S3ConditionalDatasetPublisher",
    "S3ConditionalWriteCapabilityErrorV2",
    "S3DatasetVersionStoreV2",
]
