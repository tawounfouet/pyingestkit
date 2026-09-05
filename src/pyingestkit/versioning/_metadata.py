from __future__ import annotations

from datetime import UTC, datetime

from pyingestkit.metadata import MetadataStore, VersionMetadataCapability
from pyingestkit.metadata.models import (
    DatasetVersionRecord,
    DatasetVersionRunRecord,
    PublishedDatasetRecord,
)

from .models import DatasetVersion, PublishedDataset


def record_version(metadata_store: MetadataStore | None, version: DatasetVersion) -> None:
    if isinstance(metadata_store, VersionMetadataCapability):
        metadata_store.record_dataset_version(
            DatasetVersionRecord(
                dataset_id=version.dataset_id,
                version_id=version.version_id,
                fingerprint=version.fingerprint.id,
                snapshot_uri=version.snapshot_uri,
                created_from_run_id=version.created_from_run_id,
                job_id=version.job_id,
                job_version=version.job_version,
                source_artifact_id=version.source_artifact_id,
                source_raw_sha256=version.source_raw_sha256,
                created_at=version.created_at,
            )
        )


def record_version_run(
    metadata_store: MetadataStore | None,
    version: DatasetVersion,
    run_id: str,
) -> None:
    if isinstance(metadata_store, VersionMetadataCapability):
        metadata_store.record_dataset_version_run(
            DatasetVersionRunRecord(
                dataset_id=version.dataset_id,
                version_id=version.version_id,
                run_id=run_id,
                created_at=datetime.now(UTC),
            )
        )


def record_published(
    metadata_store: MetadataStore | None,
    published: PublishedDataset,
) -> None:
    if isinstance(metadata_store, VersionMetadataCapability):
        metadata_store.record_published_dataset(
            PublishedDatasetRecord(
                dataset_id=published.dataset_id,
                version_id=published.version_id,
                published_from_run_id=published.published_from_run_id,
                published_at=published.published_at,
            )
        )
